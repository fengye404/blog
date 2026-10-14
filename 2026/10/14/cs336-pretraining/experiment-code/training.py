import numpy as np
import torch


def cross_entropy(logits, targets):
    # logits: (..., vocab_size)，targets: (...)
    z = logits.float()
    z = z - z.max(dim=-1, keepdim=True).values
    log_normalizer = torch.log(torch.exp(z).sum(dim=-1))
    correct_logits = z.gather(-1, targets.unsqueeze(-1)).squeeze(-1)
    return (log_normalizer - correct_logits).mean()


import math


class AdamW(torch.optim.Optimizer):
    def __init__(self, params, lr=1e-3, betas=(0.9, 0.95),
                 eps=1e-8, weight_decay=0.1):
        super().__init__(params, dict(
            lr=lr, betas=betas, eps=eps, weight_decay=weight_decay
        ))

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            beta1, beta2 = group["betas"]
            lr = group["lr"]
            for param in group["params"]:
                if param.grad is None:
                    continue
                grad = param.grad
                state = self.state[param]
                if not state:
                    state["t"] = 0
                    state["m"] = torch.zeros_like(param)
                    state["v"] = torch.zeros_like(param)

                state["t"] += 1
                t, m, v = state["t"], state["m"], state["v"]
                m.mul_(beta1).add_(grad, alpha=1 - beta1)
                v.mul_(beta2).addcmul_(grad, grad, value=1 - beta2)

                adjusted_lr = lr * math.sqrt(1 - beta2**t) / (1 - beta1**t)
                param.mul_(1 - lr * group["weight_decay"])
                param.addcdiv_(m, v.sqrt().add_(group["eps"]),
                               value=-adjusted_lr)
        return loss


def cosine_lr(t, max_lr, min_lr, warmup_steps, total_steps):
    if not 0 <= warmup_steps < total_steps:
        raise ValueError("require 0 <= warmup_steps < total_steps")
    if t < warmup_steps:
        return max_lr * t / warmup_steps
    if t >= total_steps:
        return min_lr
    progress = (t - warmup_steps) / (total_steps - warmup_steps)
    return min_lr + 0.5 * (1 + math.cos(math.pi * progress)) * (max_lr - min_lr)


@torch.no_grad()
def clip_gradients(parameters, max_norm, eps=1e-6):
    grads = [p.grad for p in parameters if p.grad is not None]
    if not grads:
        return 0.0
    norm = torch.stack([g.float().square().sum() for g in grads]).sum().sqrt()
    scale = (max_norm / (norm + eps)).clamp(max=1.0)
    for grad in grads:
        grad.mul_(scale)
    return norm.item()


def get_batch(data, batch_size, seq_len, device, rng):
    if len(data) <= seq_len:
        raise ValueError("data must contain at least seq_len + 1 tokens")
    starts = rng.integers(0, len(data) - seq_len, size=batch_size)
    x = np.stack([data[i:i + seq_len] for i in starts]).astype(np.int64)
    y = np.stack([data[i + 1:i + seq_len + 1] for i in starts]).astype(np.int64)
    return torch.from_numpy(x).to(device), torch.from_numpy(y).to(device)


def save_checkpoint(path, model, optimizer, step):
    torch.save({
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "step": step,
    }, path)


def load_checkpoint(path, model, optimizer):
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model"])
    optimizer.load_state_dict(checkpoint["optimizer"])
    return checkpoint["step"]


@torch.no_grad()
def evaluate(model, data, batch_size, seq_len, device, batches=20):
    was_training = model.training
    model.eval()
    # 每次验证使用相同的抽样窗口，减少曲线中由抽样带来的波动。
    rng = np.random.default_rng(2026)
    losses = []
    try:
        for _ in range(batches):
            x, y = get_batch(data, batch_size, seq_len, device, rng)
            losses.append(cross_entropy(model(x), y).item())
    finally:
        model.train(was_training)
    return sum(losses) / len(losses)


import json
import time
from pathlib import Path


def train(model, optimizer, train_data, val_data, device, run_dir,
          batch_size=32, seq_len=256, total_steps=5000,
          max_lr=1e-3, min_lr=1e-4, warmup_steps=100,
          max_norm=1.0, start_step=0):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    started = time.perf_counter()
    model.train()

    with (run_dir / "metrics.jsonl").open("a") as log:
        for step in range(start_step, total_steps):
            lr = cosine_lr(step, max_lr, min_lr, warmup_steps, total_steps)
            for group in optimizer.param_groups:
                group["lr"] = lr

            x, y = get_batch(train_data, batch_size, seq_len, device, rng)
            optimizer.zero_grad(set_to_none=True)
            loss = cross_entropy(model(x), y)
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite loss at step {step}")
            loss.backward()
            grad_norm = clip_gradients(model.parameters(), max_norm)
            if not math.isfinite(grad_norm):
                raise RuntimeError(f"non-finite gradient at step {step}")
            optimizer.step()

            completed = step + 1
            if completed % 100 == 0 or completed == total_steps:
                val_loss = evaluate(model, val_data, batch_size, seq_len, device)
                record = dict(
                    step=completed,
                    tokens=completed * batch_size * seq_len,
                    seconds=time.perf_counter() - started,
                    train_loss=loss.item(), val_loss=val_loss,
                    lr=lr, grad_norm=grad_norm,
                )
                log.write(json.dumps(record) + "\n")
                log.flush()
                print(record)

            if completed % 1000 == 0 or completed == total_steps:
                save_checkpoint(run_dir / f"step-{completed}.pt",
                                model, optimizer, completed)


@torch.no_grad()
def generate(model, prompt_ids, max_new_tokens, context_length,
             eos_id, temperature=0.8, top_p=0.9):
    # 为了看清采样逻辑，这里一次生成一条序列。
    if len(prompt_ids) == 0 or temperature < 0 or not 0 < top_p <= 1:
        raise ValueError("invalid prompt or sampling settings")
    device = next(model.parameters()).device
    tokens = torch.tensor([prompt_ids], dtype=torch.long, device=device)
    was_training = model.training
    model.eval()
    try:
        for _ in range(max_new_tokens):
            logits = model(tokens[:, -context_length:])[:, -1, :].float()
            if temperature == 0:
                next_id = logits.argmax(dim=-1, keepdim=True)
            else:
                probs = torch.softmax(logits / temperature, dim=-1)
                sorted_probs, indices = probs.sort(dim=-1, descending=True)
                # 当前 token 之前的累计概率小于 p，就保留当前 token。
                remove = sorted_probs.cumsum(dim=-1) - sorted_probs >= top_p
                sorted_probs.masked_fill_(remove, 0)
                sorted_probs /= sorted_probs.sum(dim=-1, keepdim=True)
                choice = torch.multinomial(sorted_probs, num_samples=1)
                next_id = indices.gather(-1, choice)
            tokens = torch.cat([tokens, next_id], dim=-1)
            if next_id.item() == eos_id:
                break
    finally:
        model.train(was_training)
    return tokens[0].tolist()
