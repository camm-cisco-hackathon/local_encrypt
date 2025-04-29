from datetime import datetime
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import json
import base64
import cv2
import os
import time
import numpy as np
import asyncio
from glob import glob
import encrypt  # Import our encryption module
import tempfile

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create all necessary directories if they don't exist
os.makedirs("./record", exist_ok=True)
os.makedirs("./record_mosaic", exist_ok=True)
os.makedirs("./record_encrypt", exist_ok=True)

INTERVAL = 0.2
frame_interval = INTERVAL
width, height = 1920, 1080  # Camera resolution settings

# Local camera processing task
async def process_local_camera():
    print("[INFO] process_local_camera task started")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    frame_count = 0
    last_saved_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Cannot read frame from local camera")
                break

            now = time.time()
            if now - last_saved_time >= frame_interval:
                filename = f"frame_{frame_count:04d}.jpg"
                file_path = f"./record/{filename}"
                cv2.imwrite(file_path, frame)
                last_saved_time = now

                try:
                    # Apply face mosaic
                    mosaic_img = encrypt.apply_face_mosaic(frame)
                    mosaic_path = f"./record_mosaic/{filename}"
                    cv2.imwrite(mosaic_path, mosaic_img)

                    # Encrypt original image
                    key = encrypt.generate_key(encrypt.ENCRYPTION_KEY)
                    encrypt_path = f"./record_encrypt/{filename}.enc"
                    encrypt.encrypt_file(file_path, key, encrypt_path)

                    # Delete original after mosaic & encrypt
                    if os.path.exists(mosaic_path) and os.path.exists(encrypt_path):
                        os.remove(file_path)
                        print(f"[Processed] {filename}")
                        frame_count += 1
                except Exception as e:
                    print(f"Error processing image: {e}")

            await asyncio.sleep(0.01)

    except Exception as e:
        print(f"Local camera stream error: {e}")
    finally:
        cap.release()
        print("[INFO] Local camera processing stopped")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    streaming = False
    use_decryption = False
    decryption_key = None

    while True:
        try:
            receive_task = asyncio.create_task(websocket.receive_text())

            if streaming:
                timer_task = asyncio.create_task(asyncio.sleep(INTERVAL))
                done, pending = await asyncio.wait(
                    [receive_task, timer_task], return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()

                if timer_task in done:
                    # Choose mosaic or decrypt
                    if use_decryption and decryption_key:
                        encrypted_frames = sorted(glob("./record_encrypt/frame_*.jpg.enc"))
                        if encrypted_frames:
                            enc = encrypted_frames[-1]
                            original = os.path.basename(enc)[:-4]
                            try:
                                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                                    tmp_path = tmp.name
                                encrypt.decrypt_file(enc, decryption_key, tmp_path)
                                img = cv2.imread(tmp_path)
                                os.unlink(tmp_path)
                                if img is not None:
                                    _, buf = cv2.imencode('.jpg', img)
                                    data_b64 = base64.b64encode(buf).decode()
                                    await websocket.send_json({
                                        'type': 'stream_frame',
                                        'data': data_b64,
                                        'filename': original,
                                        'decrypted': True
                                    })
                            except Exception as e:
                                print(f"Decryption error: {e}")
                                use_decryption = False
                                await websocket.send_json({
                                    'type': 'decryption_error',
                                    'message': 'Failed to decrypt. Falling back to mosaic.'
                                })
                    else:
                        frames = sorted(glob("./record_mosaic/frame_*.jpg"))
                        if frames:
                            img = cv2.imread(frames[-1])
                            if img is not None:
                                _, buf = cv2.imencode('.jpg', img)
                                data_b64 = base64.b64encode(buf).decode()
                                await websocket.send_json({
                                    'type': 'stream_frame',
                                    'data': data_b64,
                                    'filename': os.path.basename(frames[-1]),
                                    'decrypted': False
                                })
                    continue
            else:
                await receive_task

            message = receive_task.result()
            data = json.loads(message)

            if data['type'] == 'stream_request':
                streaming = True
                # Immediately send one frame on start
                frames = sorted(glob("./record_mosaic/frame_*.jpg"))
                if frames:
                    img = cv2.imread(frames[-1])
                    if img is not None:
                        _, buf = cv2.imencode('.jpg', img)
                        data_b64 = base64.b64encode(buf).decode()
                        await websocket.send_json({
                            'type': 'stream_frame',
                            'data': data_b64,
                            'filename': os.path.basename(frames[-1]),
                            'decrypted': False
                        })

            elif data['type'] == 'stop_stream':
                streaming = False
                await websocket.send_json({'type': 'stream_complete'})

            elif data['type'] == 'set_decryption_key':
                key_input = data.get('key')
                if key_input:
                    try:
                        key = encrypt.generate_key(key_input)
                        files = glob("./record_encrypt/*.enc")
                        if files:
                            test = files[0]
                            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                                tmp_p = tmp.name
                            encrypt.decrypt_file(test, key, tmp_p)
                            os.unlink(tmp_p)
                            decryption_key = key
                            use_decryption = True
                            await websocket.send_json({
                                'type': 'decryption_key_valid',
                                'message': 'Key accepted. Streaming original.'
                            })
                    except Exception as e:
                        print(f"Invalid key: {e}")
                        await websocket.send_json({
                            'type': 'decryption_key_invalid',
                            'message': 'Invalid decryption key.'
                        })
                else:
                    use_decryption = False
                    decryption_key = None
                    await websocket.send_json({
                        'type': 'decryption_disabled',
                        'message': 'Decryption disabled. Streaming mosaic.'
                    })
        except Exception as e:
            print(f"WebSocket error: {e}")
            break

# Helper to delete old files

def del_files():
    # Delete all files in ./record directory
    for file in os.listdir("./record"):
        os.remove(os.path.join("./record", file))
    for file in os.listdir("./record_mosaic"):
        os.remove(os.path.join("./record_mosaic", file))
    for file in os.listdir("./record_encrypt"):
        os.remove(os.path.join("./record_encrypt", file))

# Start RTSP processing and process existing images when the server starts
@app.on_event("startup")
async def startup_event():
    print("[INFO] Application startup - cleaning folders, launching camera task")
    del_files()

    # Process any existing images
    encrypt.process_files()
    
    # Start RTSP processing task
    asyncio.create_task(process_local_camera())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=52049)