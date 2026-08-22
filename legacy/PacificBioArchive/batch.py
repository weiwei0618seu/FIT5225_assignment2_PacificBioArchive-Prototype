# Batch processing of camera-trap images using MegaDetector and fine-tuned SpeciesNet.

# This script demonstrates how to use MegaDetector to detect animals in a batch of camera-trap images, and then apply a fine-tuned SpeciesNet model to classify the detected animals. The script is structured as follows:
# 1. Load and run MegaDetector on a batch of images.
# 2. Extract the detected bounding boxes and save cropped images of the detected animals.
# 3. Load a fine-tuned SpeciesNet model and classify the cropped images.

from pathlib import Path
from megadetector.detection import run_detector_batch
import os
import json
import warnings
warnings.filterwarnings('ignore')
import json
import os
from pathlib import Path
from PIL import Image
import yaml
from tqdm import tqdm
import torch
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt

input_dir = Path("./images")

output_file = Path("./mg_detections.json")
files = []

for file in os.listdir(os.path.join(input_dir)):
    if not (file.startswith(".") or file.startswith("..")):
        files.append(os.path.join(input_dir, file))

print(f"Running MegaDetector on {len(files)} images...")
data = run_detector_batch.load_and_run_detector_batch(image_file_names=files, model_file="./mdv5a.pt")
with open(output_file, "w") as file:
    json.dump(data, file)

# The results of MegaDetector are stord in the "mg_detections" json file. We will now extract the information from the json file to save the cropped images in a new folder called "cropped_images".

# Using MEWC-snip (https://github.com/zaandahl/mewc-snip/blob/main/src/mewc_snip.py) to create the crops. <br> <br>
# Variable	Default	Description <br>
# INPUT_DIR	"/images/"	A mounted point containing images to process - must match the Docker command above <br>
# MD_FILE	"mg_detections.json"	MegaDetector output file <br>
# SNIP_DIR	"cropped_images"	A directory to save snips (will be created if it does not exist) <br>
# LOWER_CONF	0.05	The lowest detection confidence threshold to accept for snipping <br>
# SNIP_SIZE	600	The pixel size for the saved snips (square) <br>

# --------------------
# Read YAML config
# --------------------
def read_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

# --------------------
# Load config
# --------------------
config = read_yaml("config.yaml")

for k in config:
    if k in os.environ:
        config[k] = os.environ[k]

INPUT_DIR = Path(config["INPUT_DIR"])
OUTPUT_DIR = Path(config["SNIP_DIR"])
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONF_THRESH = float(config["LOWER_CONF"])
SNIP_SIZE = int(config["SNIP_SIZE"])

# --------------------
# Load MD output
# --------------------
json_path = Path(config["MD_FILE"])

with open(json_path, "r") as f:
    md_data = json.load(f)

print(f"Processing {len(md_data)} images.")

# --------------------
# Main loop (MEWC-snip equivalent)
# --------------------
for entry in md_data:
    img_path = entry["file"]
    # print(img_path)
    if not Path(img_path).exists():
        continue
    detections = entry["detections"]
    
    img = Image.open(img_path)
    width, height = img.size

    max_conf = entry["max_detection_conf"]

    crop_num = 0
    for i, detection in enumerate(detections):
        conf= detection["conf"]
        if detection["category"] != "1":
            continue       

        img = Image.open(img_path).convert("RGB")
        W, H = img.size        

        if conf < CONF_THRESH:
            continue

        x, y, w, h = detection["bbox"]

        left = int(x * W)
        top = int(y * H)
        right = int((x + w) * W)
        bottom = int((y + h) * H)

        crop = img.crop((left, top, right, bottom))

        # Resize rectangular crop
        resized = crop.resize(
            (SNIP_SIZE, SNIP_SIZE),
            Image.BILINEAR
        )

        out_name = (
            f"{Path(img_path).stem}"
            f"-{crop_num}"
            f"{Path(img_path).suffix}"
        )

        resized.save(OUTPUT_DIR / out_name)
        print("Saved the cropped image at", OUTPUT_DIR / out_name)
        crop_num += 1

# ## Running fine-tuned SpeciesNet on test images
print(torch.__version__)

MODEL_PT_PATH = "./model.pt" # WildObs National model
if torch.cuda.is_available():   # for NVIDIA GPUs
    DEVICE = "cuda"
elif torch.backends.mps.is_available(): # for Apple Silicon devices
    DEVICE = "mps"
else:
    DEVICE = "cpu"
print("Using device:", DEVICE)

# supported classes in the model
classes = ['Alectura_lathami', 'Antechinus_agilis', 'Bos_taurus', 'Burhinus_grallarius', 'Canis_familiaris', 'Chalcophaps_longirostris', 'Colluricincla_harmonica', 'Corcorax_melanorhamphos', 'Dacelo_novaeguineae', 'Dama_dama', 'Eopsaltria_australis', 'Felis_catus', 'Geopelia_humeralis', 'Gymnorhina_tibicen', 'Homo_sapiens', 'Isoodon_macrourus', 'Lepus_europaeus', 'Macropus_giganteus', 'Menura_novaehollandiae', 'Mus_musculus', 'Oryctolagus_cuniculus', 'Perameles_nasuta', 'Pitta_versicolor', 'Rattus', 'Rattus_fuscipes', 'Rattus_rattus', 'Strepera_graculina', 'Sus_scrofa', 'Tachyglossus_aculeatus', 'Thylogale_stigmatica', 'Trichosurus_caninus', 'Trichosurus_cunninghami', 'Trichosurus_vulpecula', 'Varanus_varius', 'Vombatus_ursinus', 'Vulpes_vulpes', 'Wallabia_bicolor', 'Canis_dingo', 'Capra_hircus', 'Casuarius_casuarius', 'Heteromyias_cinereifrons', 'Hypsiprymnodon_moschatus', 'Megapodius_reinwardt', 'Notamacropus_rufogriseus', 'Orthonyx_spaldingii', 'Uromys_caudimaculatus']

model = torch.load(MODEL_PT_PATH, map_location=DEVICE,weights_only=False)
model.eval()
model.to(DEVICE)

print("Loaded fine-tuned model")

# Transform to be applied on the images before applying the model
transform = transforms.Compose([
    transforms.Resize((480, 480)),
    transforms.ToTensor(),
])

@torch.no_grad()
def classify_image(image_path):

    img = Image.open(image_path).convert("RGB")

    # show the image
    plt.imshow(img)
    plt.axis('off')
    plt.title(image_path)
    plt.show()

    img = transform(img)           # -> C,H,W
    img = img.unsqueeze(0)         # -> B,C,H,W
    img = img.permute(0,2,3,1)     # -> B,H,W,C

    img = img.to(DEVICE)

    logits = model(img)
    probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

    # sort by confidence
    order = np.argsort(probs)[::-1]

    print("\n---- PREDICTIONS ----")
    for idx in order:
        label = classes[idx]
        confidence = probs[idx]
        print(f"{label:<25}  {confidence:.4f}")

    best_idx = order[0]
    print("\n FINAL PREDICTION:")
    print(f"Species: {classes[best_idx]}")
    print(f"Confidence: {probs[best_idx]:.4f}")

TEST_IMAGE_PATH = "./cropped_images/Alectura_lathami_1-0.JPG"

classify_image(TEST_IMAGE_PATH)