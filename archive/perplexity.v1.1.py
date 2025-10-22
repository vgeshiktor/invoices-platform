import os
import time

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

url = "https://myinvoice.bezeq.co.il/?MailID=15092514451814583A4F27F10C8E91CA24C9CCA0286648A56F792F5148E4B521E8C290A36BB7B0B217BCC1F881FD3FAC4A6A5C9E4053F3B3016C79030002F69C7E4A2184E59517C&utm_source=bmail&utm_medium=email&utm_campaign=bmail&WT.mc_id=bmail"

download_dir = os.path.join(os.getcwd(), "invoices")
os.makedirs(download_dir, exist_ok=True)

chrome_options = Options()
# chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
driver = webdriver.Chrome(options=chrome_options)
driver.get(url)

print("טוען את החשבונית...")
time.sleep(10)

# חיפוש iframe שמכיל את החשבונית
iframes = driver.find_elements(By.TAG_NAME, "iframe")
pdf_url = None

for frame in iframes:
    print(frame.get_attribute("src"))
    src = frame.get_attribute("src")
    if src and ".pdf" in src:
        pdf_url = src
        break

if pdf_url:
    print("נמצא קובץ PDF – מוריד...")
    response = requests.get(pdf_url)
    pdf_path = os.path.join(download_dir, "bezeq_invoice.pdf")
    with open(pdf_path, "wb") as f:
        f.write(response.content)
    print("החשבונית נשמרה:", pdf_path)
else:
    print("לא נמצא iframe עם קובץ PDF. ייתכן שהמערכת דורשת אישור נוסף או לחיצה ידנית.")

driver.quit()
