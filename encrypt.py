import cv2
import os
import glob
import numpy as np
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Define directories
INPUT_DIR = "./record"
MOSAIC_DIR = "./record_mosaic"
ENCRYPT_DIR = "./record_encrypt"
ENCRYPTION_KEY = "asdf"

# Create output directories if they don't exist
os.makedirs(MOSAIC_DIR, exist_ok=True)
os.makedirs(ENCRYPT_DIR, exist_ok=True)

# Load face detection model
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def generate_key(password):
    """Generate encryption key from password"""
    password = password.encode()
    salt = b'salt_'  # In production, use a secure random salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key

def encrypt_file(file_path, key, output_path):
    """Encrypt a file using Fernet symmetric encryption"""
    fernet = Fernet(key)
    with open(file_path, 'rb') as file:
        file_data = file.read()
    encrypted_data = fernet.encrypt(file_data)
    with open(output_path, 'wb') as file:
        file.write(encrypted_data)

def decrypt_file(file_path, key, output_path):
    """Decrypt a file using Fernet symmetric encryption"""
    fernet = Fernet(key)
    with open(file_path, 'rb') as file:
        encrypted_data = file.read()
    decrypted_data = fernet.decrypt(encrypted_data)
    with open(output_path, 'wb') as file:
        file.write(decrypted_data)

def apply_face_mosaic(image, scale=0.1):
    """Detect faces and apply mosaic effect using YOLO"""
    try:
        import ultralytics
        from ultralytics import YOLO
        
        model = YOLO("yolov11n-face.pt")
        
        # Create a copy for modification
        result_image = image.copy()
        
        # Run inference on the image
        results = model(image)
        
        # Process detected faces
        if results and len(results) > 0:
            for result in results[0].boxes.data:
                x1, y1, x2, y2, conf, class_id = result
                
                # Convert to integers
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Extract the face region
                face_roi = result_image[y1:y2, x1:x2]
                
                # Apply mosaic effect (downscale and upscale)
                small = cv2.resize(face_roi, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
                face_roi_mosaic = cv2.resize(small, (x2-x1, y2-y1), interpolation=cv2.INTER_NEAREST)
                
                # Replace the face region with the mosaic version
                result_image[y1:y2, x1:x2] = face_roi_mosaic
                
        return result_image
        
    except Exception as e:
        print(f"Error in YOLO face detection: {e}")
        # Fallback to Haar cascade if YOLO fails
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        # Create a copy for modification
        result_image = image.copy()
        
        for (x, y, w, h) in faces:
            # Extract the face region
            face_roi = result_image[y:y+h, x:x+w]
            
            # Apply mosaic effect (downscale and upscale)
            small = cv2.resize(face_roi, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
            face_roi_mosaic = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
            
            # Replace the face region with the mosaic version
            result_image[y:y+h, x:x+w] = face_roi_mosaic
            
        return result_image

def process_files():
    """Process all images in the input directory"""
    # Generate encryption key
    key = generate_key(ENCRYPTION_KEY)
    
    # Get all jpg files in the input directory
    files = glob.glob(f"{INPUT_DIR}/*.jpg")
    
    # Process each file
    for file_path in files:
        filename = os.path.basename(file_path)
        mosaic_path = os.path.join(MOSAIC_DIR, filename)
        encrypt_path = os.path.join(ENCRYPT_DIR, filename + ".enc")
        
        # Skip if already processed
        if os.path.exists(mosaic_path) and os.path.exists(encrypt_path):
            continue
        
        # Read image
        image = cv2.imread(file_path)
        if image is None:
            print(f"Failed to read {file_path}")
            continue
        
        # Apply face mosaic
        mosaic_image = apply_face_mosaic(image)
        
        # Save mosaic image
        cv2.imwrite(mosaic_path, mosaic_image)
        
        # Encrypt and save original image
        encrypt_file(file_path, key, encrypt_path)
        
        # Delete original image after mosaicking and encryption
        if os.path.exists(mosaic_path) and os.path.exists(encrypt_path):
            os.remove(file_path)
            # print(f"Deleted original: {filename}")
        
        # print(f"Processed: {filename}")

def main():
    """Main function"""
    process_files()
    print("Processing complete!")

if __name__ == "__main__":
    main()
