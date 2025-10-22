import requests


def download_pdf(url, save_path):
    """
    Downloads a file from a given URL and saves it to a specified path.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url, stream=True)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Check if the content is actually a PDF
            if "application/pdf" in response.headers.get("Content-Type", ""):
                # Open the save path in write-binary mode
                with open(save_path, "wb") as f:
                    # Write the content of the response to the file
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Successfully downloaded PDF to: {save_path}")
            else:
                print("Error: The URL does not point directly to a PDF file.")
                print(f"Content-Type received: {response.headers.get('Content-Type')}")

        else:
            print(
                f"Error: Failed to retrieve file. Status code: {response.status_code}"
            )

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")


# --- --- --- --- --- --- --- --- --- --- ---
# --- --- --- --- --- --- --- --- --- --- ---
# WARNING: Read the notes below before running
# --- --- --- --- --- --- --- --- --- --- ---
# --- --- --- --- --- --- --- --- --- --- ---

# The URL you provided
invoice_url = "https://myinvoice.bezeq.co.il/?MailID=15092514451814583A4F27F10C8E91CA24C9CCA0286648A56F792F5148E4B521E8C290A36BB7B0B217BCC1F881FD3FAC4A6A5C9E4053F3B3016C79030002F69C7E4A2184E59517C&utm_source=bmail&utm_medium=email&utm_campaign=bmail&WT.mc_id=bmail"

# The name you want to save the file as
file_to_save = "my_invoice.pdf"

# Run the download function
# download_pdf(invoice_url, file_to_save)
# --- --- --- --- --- --- --- --- --- --- ---
