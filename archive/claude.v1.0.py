"""
סקריפט להורדת חשבונית PDF מאתר בזק
נדרש להתקין: pip install requests beautifulsoup4 selenium
"""

import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def download_pdf_simple(url, output_filename="bezeq_invoice.pdf"):
    # sourcery skip: extract-duplicate-method, extract-method
    """
    גישה ראשונה: ניסיון הורדה ישיר של PDF
    """
    print("מנסה להוריד PDF בשיטה פשוטה...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        session = requests.Session()
        response = session.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()

        # בדיקה אם התגובה היא PDF
        if "application/pdf" in response.headers.get("Content-Type", ""):
            with open(output_filename, "wb") as f:
                f.write(response.content)
            print(f"✓ PDF הורד בהצלחה: {output_filename}")
            return True

        # אם זה HTML, מחפשים קישורים ל-PDF בעמוד
        soup = BeautifulSoup(response.content, "html.parser")

        # חיפוש קישורים לPDF
        pdf_links = []
        for link in soup.find_all("a"):
            href = link.get("href")
            if href and (".pdf" in href.lower() or "download" in href.lower()):
                full_url = urljoin(url, href)
                pdf_links.append(full_url)

        # חיפוש כפתורים או אלמנטים עם onclick
        for element in soup.find_all(["button", "div", "span"]):
            onclick = element.get("onclick", "")
            if "pdf" in onclick.lower() or "download" in onclick.lower():
                print(f"נמצא אלמנט עם onclick: {onclick}")

        if pdf_links:
            print(f"נמצאו {len(pdf_links)} קישורי PDF אפשריים:")
            for i, link in enumerate(pdf_links, 1):
                print(f"{i}. {link}")

            # מנסים להוריד את הקישור הראשון
            print(f"\nמנסה להוריד: {pdf_links[0]}")
            pdf_response = session.get(pdf_links[0], headers=headers)

            if pdf_response.status_code == 200:
                with open(output_filename, "wb") as f:
                    f.write(pdf_response.content)
                print(f"✓ PDF הורד בהצלחה: {output_filename}")
                return True

        print("לא נמצא קישור ישיר ל-PDF בעמוד")
        return False

    except Exception as e:
        print(f"שגיאה: {str(e)}")
        return False


def download_with_selenium(url, output_filename="bezeq_invoice.pdf"):
    """
    גישה שנייה: שימוש ב-Selenium לטיפול בדפים דינמיים
    נדרש להתקין: pip install selenium
    ולהוריד ChromeDriver מ: https://chromedriver.chromium.org/
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC  # noqa: F401
        from selenium.webdriver.support.ui import WebDriverWait  # noqa: F401

        print("מנסה להוריד PDF באמצעות Selenium...")

        # הגדרות Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # רצה ברקע ללא חלון
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # הגדרות להורדה אוטומטית של PDF
        download_dir = os.path.abspath(os.getcwd())
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        driver = webdriver.Chrome(options=chrome_options)

        try:
            driver.get(url)
            time.sleep(3)  # המתנה לטעינת הדף

            if download_buttons := driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '.pdf')] | //button[contains(text(), 'הורד')] | //a[contains(text(), 'הורד')]",
            ):
                print(f"נמצאו {len(download_buttons)} כפתורי הורדה אפשריים")
                download_buttons[0].click()
                print("לחץ על כפתור ההורדה, ממתין לקובץ...")
                time.sleep(5)  # המתנה להורדה

                # בדיקה אם הקובץ הורד
                for file in os.listdir(download_dir):
                    if file.endswith(".pdf"):
                        os.rename(file, output_filename)
                        print(f"✓ PDF הורד בהצלחה: {output_filename}")
                        return True

            # אם לא נמצא כפתור, נבדוק אם הדף עצמו הוא PDF
            if driver.current_url.endswith(".pdf"):
                print("הדף עצמו הוא PDF, שומר...")
                # כאן צריך לטפל בשמירת הPDF
                return True

            print("לא נמצא כפתור הורדה בעמוד")
            print("תוכן הדף:")
            print(driver.page_source[:500])  # הדפסת תחילת הדף לבדיקה

            return False

        finally:
            driver.quit()

    except ImportError:
        print("Selenium לא מותקן. התקן באמצעות: pip install selenium")
        return False
    except Exception as e:
        print(f"שגיאה ב-Selenium: {str(e)}")
        return False


def main():
    # הקישור שלך
    url = "https://myinvoice.bezeq.co.il/?MailID=15092514451814583A4F27F10C8E91CA24C9CCA0286648A56F792F5148E4B521E8C290A36BB7B0B217BCC1F881FD3FAC4A6A5C9E4053F3B3016C79030002F69C7E4A2184E59517C&utm_source=bmail&utm_medium=email&utm_campaign=bmail&WT.mc_id=bmail"

    output_file = "bezeq_invoice.pdf"

    print("=== מתחיל הורדת חשבונית מבזק ===\n")

    # ניסיון ראשון - הורדה פשוטה
    if download_pdf_simple(url, output_file):
        print("\n✓ ההורדה הצליחה!")
        return

    print("\n--- מעבר לשיטה מתקדמת ---\n")

    # ניסיון שני - Selenium
    if download_with_selenium(url, output_file):
        print("\n✓ ההורדה הצליחה!")
        return

    print("\n✗ ההורדה נכשלה בכל השיטות")
    print("\nהערות חשובות:")
    print("1. הדף דורש כנראה התחברות אישית")
    print("2. אפשר לנסות להיכנס ידנית לדף ולהעתיק cookies")
    print("3. אפשר להשתמש בתוסף דפדפן להורדת החשבונית")
    print("4. ניתן לשמור את העמוד כ-PDF ידנית (Ctrl+P)")


if __name__ == "__main__":
    main()
