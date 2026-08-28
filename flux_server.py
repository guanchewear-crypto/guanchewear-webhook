"""
GuancheWear - Local FLUX Image Generation Server
Ejecutar: python flux_server.py
Expone API en http://localhost:8010
"""
import io
import base64
import time
import os
import sys
from pathlib import Path

# Cache dir for models
os.environ["HF_HOME"] = str(Path.home() / "flux-models")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="GuancheWear FLUX Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Global: model loaded once
pipe = None

class GenerateRequest(BaseModel):
    prompt: str
    num_images: int = 2
    width: int = 512
    height: int = 512

class GenerateResponse(BaseModel):
    images: list[str]
    inference_time: float
    model: str

@app.on_event("startup")
def load_model():
    global pipe
    print("⏳ Cargando Stable Diffusion XL...")
    t0 = time.time()
    from diffusers import StableDiffusionXLPipeline
    import torch
    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16,
        use_safetensors=True,
        variant="fp16"
    )
    pipe.enable_model_cpu_offload()
    if hasattr(pipe, 'enable_vae_slicing'):
        pipe.enable_vae_slicing()
    if hasattr(pipe, 'enable_vae_tiling'):
        pipe.enable_vae_tiling()
    print(f"✅ Stable Diffusion XL cargado en {time.time()-t0:.1f}s")

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": pipe is not None}

@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    global pipe
    if pipe is None:
        return GenerateResponse(images=[], inference_time=0, model="not_loaded")

    images_b64 = []
    t0 = time.time()
    import torch
    generator = torch.Generator("cuda") if torch.cuda.is_available() else None

    for i in range(req.num_images):
        out = pipe(
            prompt=req.prompt,
            num_inference_steps=25,
            width=req.width,
            height=req.height,
            generator=generator if i == 0 else (torch.Generator("cuda").manual_seed(int(time.time()*1000)%(2**32)) if torch.cuda.is_available() else None),
        ).images[0]

        buf = io.BytesIO()
        out.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        images_b64.append(f"data:image/png;base64,{b64}")

    elapsed = time.time() - t0
    return GenerateResponse(
        images=images_b64,
        inference_time=round(elapsed, 2),
        model="FLUX.1-schnell"
    )

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8010
    print(f"🚀 FLUX server en http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)