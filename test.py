# import pytesseract
# from PIL import Image


# pytesseract.pytesseract.tesseract_cmd = r'<full_path_to_your_tesseract_executable>'
# print(pytesseract.image_to_string(Image.open("images/test.png")))

from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import json

# model = ocr_predictor(pretrained=True)
predictor = ocr_predictor(
    det_arch="db_mobilenet_v3_large",
    reco_arch="crnn_mobilenet_v3_small",
    pretrained=True,
)

image = DocumentFile.from_images(r"images\yugan.999\C94-KWnxNAB.jpg")

result = predictor(image)

result_json = result.export()

# print(json.dumps(result_json, indent=4))

result.show()
string_result = result.render()
print(string_result)