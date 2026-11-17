"""在 Qwen2.5-1.5B-Instruct 上做 LoRA SFT：学「摄影师怎么说话」。

2026-11-16 · 拍社第七轮 P0（用户 Q1 选 A：1.5B + bf16 LoRA）。
语料：ai-classifier/distill/corpus.jsonl（人工撰写，格式 {p,u,a[,c]}）。
只对 assistant 部分算 loss（system/user 全部 mask 成 -100），否则模型会学成复读用户。

2026-11-16 第十轮补充（治「编价格 / 细节」）：
  线上 compose_model() 在 system 之后还会插一条 `已知信息：price=…、nextSlot=…` 的 system 消息，
  但原来训练只拼 system(人设)+user+assistant，模型从没见过事实层，于是按人设自由发挥编价。
  现在语料可带 "c"（price/nextSlot/count/city），encode() 按**和推理完全一致的格式**插入这条 system，
  让「只引用给定数字、没有就给『确认下』」成为学得到的行为。

跑法（cwd = 仓库根）：
  .staging\\.venv-train\\Scripts\\python.exe ai-classifier\\distill\\train_lora.py
产物（可用 CHAT_OUT_ADAPTER / CHAT_OUT_MERGED 覆盖，便于训练新版时不覆盖线上在跑的模型）：
  .staging\\models\\paishe-chat-lora\\        ← LoRA adapter
  .staging\\models\\paishe-chat-merged\\      ← 合并后的完整模型（chat.py 直接加载这个）
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
import time

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "ai-classifier"))

from pipeline.chat import PERSONAS, STYLE_RULES, DEFAULT_PERSONA  # noqa: E402

MODEL_DIR = os.path.join(ROOT, ".staging", "models", "Qwen2.5-1.5B-Instruct")
DATA = os.path.join(ROOT, "ai-classifier", "distill", "corpus.jsonl")
OUT_ADAPTER = os.environ.get("CHAT_OUT_ADAPTER") or os.path.join(ROOT, ".staging", "models", "paishe-chat-lora")
OUT_MERGED = os.environ.get("CHAT_OUT_MERGED") or os.path.join(ROOT, ".staging", "models", "paishe-chat-merged")

EPOCHS = int(os.environ.get("EPOCHS", "8"))
LR = float(os.environ.get("LR", "2e-4"))
BATCH = int(os.environ.get("BATCH", "2"))
MAX_LEN = int(os.environ.get("MAX_LEN", "512"))
SEED = 20261116


def system_prompt(persona: str) -> str:
    p = PERSONAS.get(persona) or PERSONAS[DEFAULT_PERSONA]
    rules = "\n".join(f"- {r}" for r in STYLE_RULES)
    return (
        "你是一位在西安/青岛接单的摄影师，正在跟潜在客户聊天。"
        f"\n说话方式：{p['voice']}" + "\n必须遵守：\n" + rules
    )


def load_rows():
    rows = []
    with open(DATA, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            p = obj.get("p") or DEFAULT_PERSONA
            ctx = obj.get("c") or None
            rows.append({"p": p, "u": obj["u"].strip(), "a": obj["a"].strip(), "c": ctx})
    return rows


def main():
    random.seed(SEED)
    torch.manual_seed(SEED)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device} torch={torch.__version__}")

    tok = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True)
    base = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR, dtype=torch.bfloat16, low_cpu_mem_usage=True
    )
    base.gradient_checkpointing_enable()
    base.config.use_cache = False

    lora = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(base, lora)
    model.to(device)
    model.train()
    model.print_trainable_parameters()

    rows = load_rows()
    random.shuffle(rows)
    val = rows[:8]
    train = rows[8:]
    print(f"train={len(train)} val={len(val)}")

    def encode(row):
        msgs = [{"role": "system", "content": system_prompt(row["p"])}]
        # 与 chat.compose_model() 同构：有 c 就插一条「已知信息：k=v、k=v」的 system。
        # 键序沿用语料里的写法，值和线上一样是纯字符串。
        ctx_text = "、".join(
            f"{key}={value}" for key, value in (row.get("c") or {}).items() if value
        )
        if ctx_text:
            msgs.append({"role": "system", "content": f"已知信息：{ctx_text}"})
        msgs.append({"role": "user", "content": row["u"]})
        prompt_text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        prompt_ids = tok(prompt_text, add_special_tokens=False)["input_ids"]
        ans_ids = tok(row["a"] + tok.eos_token, add_special_tokens=False)["input_ids"]
        input_ids = (prompt_ids + ans_ids)[:MAX_LEN]
        labels = ([-100] * len(prompt_ids) + ans_ids)[:MAX_LEN]
        return {"input_ids": input_ids, "labels": labels}

    def collate(batch):
        width = max(len(b["input_ids"]) for b in batch)
        pad = tok.pad_token_id or tok.eos_token_id
        ids = torch.full((len(batch), width), pad, dtype=torch.long)
        labs = torch.full((len(batch), width), -100, dtype=torch.long)
        mask = torch.zeros((len(batch), width), dtype=torch.long)
        for i, b in enumerate(batch):
            n = len(b["input_ids"])
            ids[i, :n] = torch.tensor(b["input_ids"])
            labs[i, :n] = torch.tensor(b["labels"])
            mask[i, :n] = 1
        return ids.to(device), labs.to(device), mask.to(device)

    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0)
    steps_per_epoch = math.ceil(len(train) / BATCH)
    total_steps = steps_per_epoch * EPOCHS
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=max(total_steps, 1), pct_start=0.1)

    step = 0
    t0 = time.time()
    for epoch in range(1, EPOCHS + 1):
        random.shuffle(train)
        running = 0.0
        for i in range(0, len(train), BATCH):
            batch = train[i:i + BATCH]
            ids, labs, _ = collate([encode(r) for r in batch])
            out = model(input_ids=ids, labels=labs)
            loss = out.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            running += float(loss.detach())
            step += 1
            if step % 5 == 0 or step == total_steps:
                mem = torch.cuda.memory_allocated() / 1e9 if device == "cuda" else 0
                print(f"epoch {epoch}/{EPOCHS} step {step}/{total_steps} loss {running/5:.4f} "
                      f"vram {mem:.2f}GB {time.time()-t0:.0f}s", flush=True)
                running = 0.0

    # 验证集 loss（不做 early stop，只看一格）
    model.eval()
    with torch.no_grad():
        total = 0.0
        for r in val:
            ids, labs, _ = collate([encode(r)])
            total += float(model(input_ids=ids, labels=labs).loss)
        print(f"val_loss {total/max(len(val),1):.4f}", flush=True)

    os.makedirs(OUT_ADAPTER, exist_ok=True)
    model.save_pretrained(OUT_ADAPTER)
    print(f"saved adapter -> {OUT_ADAPTER}", flush=True)

    # 合并成完整模型，服务端只用加载一个目录
    merged = model.merge_and_unload()
    merged.save_pretrained(OUT_MERGED, safe_serialization=True)
    tok.save_pretrained(OUT_MERGED)
    print(f"saved merged -> {OUT_MERGED}", flush=True)


if __name__ == "__main__":
    main()
