import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# URL של החשבונית האישית
url = "https://myinvoice.bezeq.co.il/?MailID=15092514451814583A4F27F10C8E91CA24C9CCA0286648A56F792F5148E4B521E8C290A36BB7B0B217BCC1F881FD3FAC4A6A5C9E4053F3B3016C79030002F69C7E4A2184E59517C&utm_source=bmail&utm_medium=email&utm_campaign=bmail&WT.mc_id=bmail"

# מיקום תיקיית הורדות
download_dir = os.path.join(os.getcwd(), "invoices")

# הגדרות דפדפן כרום להורדת PDF אוטומטית
chrome_options = Options()
prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True,
}
chrome_options.add_experimental_option("prefs", prefs)
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")

# פתיחת הדפדפן
driver = webdriver.Chrome(options=chrome_options)
driver.get(url)

print("טוען את החשבונית...")
time.sleep(10)  # להמתין שהעמוד יטען לחלוטין

# ניסיון למצוא קישור PDF (במקרים רבים הוא גלוי כ iframe או href)
pdf_links = [
    a.get_attribute("href")
    for a in driver.find_elements("tag name", "a")
    if a.get_attribute("href") and a.get_attribute("href").endswith(".pdf")
]

if pdf_links:
    pdf_url = pdf_links[0]
    import requests

    r = requests.get(pdf_url)
    pdf_file = os.path.join(download_dir, "bezeq_invoice.pdf")
    with open(pdf_file, "wb") as f:
        f.write(r.content)
    print(f"נשמר: {pdf_file}")
else:
    print("לא נמצא קובץ PDF. ייתכן שיש צורך בהתחברות או בטעינה ארוכה יותר.")

driver.quit()
