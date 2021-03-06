import qrcode
from time import time
import requests
import sys
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText  # Added
from email.mime.image import MIMEImage
import smtplib


# Member verification and download the images from google drive
def verifyMember(p_link, status, payment):
    """
    :param p_link: the link of the student profile
    :return: true if the page is valid and contains student
    otherwise no
    """

    if status != 'Bachelor/Master student':
        # accounts for empty cell case (nan is true)
        return str(payment).upper() == 'TRUE'
    try:
        if str(p_link) != 'nan':
            page = requests.get(p_link)
            web_page = str(page.content)
            if 'Student' in web_page:
                return True
            elif 'Etudiant' in web_page:
                return True
            else:
                return False
        else:
            return False
    except Exception as e:
        print(e)
        print("http request failed. Member is not verified")
    return False


def generateQR(link):
    # Create qr code instance
    # QR code links to the generated link for each member
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    # Add data
    qr.add_data(link)
    qr.make(fit=True)

    qr_code = qr.make_image()
    temp_location = 'image.jpg'

    qr_code.save(temp_location)


def download_file_from_google_drive(id, destination):
    URL = "https://docs.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(URL, params = { 'id' : id }, stream = True)
    token = get_confirm_token(response)

    if token:
        params = { 'id' : id, 'confirm' : token }
        response = session.get(URL, params = params, stream = True)

    save_response_content(response, destination)


def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value

    return None


def save_response_content(response, destination):
    CHUNK_SIZE = 32768

    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)


def generateMemberPage(firstN, lastN, status, validity, img_path):
    # init file constants
    status = status
    exp_date = '2019.01.01'

    file_name = '../../members/' + firstN + '_' + lastN + '.md'

    # writing to file
    file = open(file_name, "w+")
    file.write('---\nlayout: post\n')
    file.write('title: ' + firstN + ' ' + lastN + '\n---\n\nStatus: ' + status + '\n')
    file.write('\nExpiration date: ' + exp_date + '\n')
    if validity:
        file.write('\nValidity: ' + '<font color="green"> Verified</font> \n')
    else:
        file.write('\nValidity: ' + '<font color="red"> Not valid</font> \n')

    file.write('![](/members/' + img_path + ')\n')
    file.write('![](/members/img/bar.png)\n')

    file.close()


def send_email(dest_email):
    attachment = 'image.jpg'

    msg = MIMEMultipart()
    msg["To"] = dest_email
    msg["From"] = "clubmontagneepfl@gmail.com"
    msg["Subject"] = "Your membership QR code"
    msg.add_header('reply-to', 'card@clubmontagne.ch')
    text = """
    <p>
        Dear Club Montagne member,
    </p>
    <p>
        Please find attached the QR-Code linked to your Club Montagne membership card.
    </p>

    <p>
        Keep it safely stored in your smartphone, and get it ready to be scanned anytime you want to use it with our partners. Attention please : our partners are free to decline your request of benefiting from your advantages unless you show your QR-Code*, make sure you have it with you before asking the people to take advantage of it!
    </p>

    <p>
        *If you are not a Bachelor nor a Master student at EPFL, you need to pay a CHF 10.- fee to activate the card. If you didn't pay yet, the card is marked as not valid. Activate the card by reaching us during rental sessions in EPFL !
    </p>
    <p>
        <a
         href="https://clubmontagne.epfl.ch/"
         target="_blank"
        >
            Click here for more information about the Club Montagne.
        </a>
    </p>
    <p>
        <a
         href="https://clubmontagne.epfl.ch/carte-membre/"
         target="_blank"
        >
            Click here for more information about the Membership Card and the advantages you get with it.
        </a>
    </p>
    <p>
        <a
         href="https://clubmontagne.epfl.ch/equipment-fr/"
         target="_blank"
        >
            Click here for more information about the Rental sessions.
        </a>
    </p>
    <p>
        Let the force be with you,
    </p>

    <p>
        Club Montagne
    </p>
    """

    content = MIMEText(text, 'html')
    msg.attach(content)

    fp = open(attachment, 'rb')
    msgText = MIMEImage(fp.read())
    msg.attach(msgText)  # Added, and edited the previous line

    ## send email
    mailserver = smtplib.SMTP('smtp.gmail.com', 587)
    # identify ourselves to smtp gmail client
    mailserver.ehlo()
    # secure our email with tls encryption
    mailserver.starttls()
    # re-identify ourselves as an encrypted connection
    mailserver.ehlo()
    mailserver.login('clubmontagneepfl@gmail.com', '<add clear text password here>')

    mailserver.sendmail('clubmontagneepfl@gmail.com', dest_email, msg.as_string())

    mailserver.quit()


def process_info(info_path):
    start = time()
    df = pd.read_csv(info_path)
    completions = []

    for index, row in df.iterrows():
        print('Starting subject ' + str(index) + ' ...')
        if_complete = True;

        # 1. validate member page
        validity = verifyMember(row['EPFL personal page link'], row['Status'], row['Payment'])

        img_name = row['First name'] + '_' + row['Last name'] + '.png'

        # 3. generate member page

        generateMemberPage(row['First name'],  row['Last name'], row['Status'],  validity, 'img/' + img_name)

        # 4. send QR code

        base_link = 'https://clubmontagne.github.io/members/'
        generateQR(base_link + row['First name'] + '_' + row['Last name'])

        # 5. send QR code to the email

        try:
            print("Sending email to: ", row['First name'], row['Last name'])
            send_email(row['Email Address'])
        except Exception as e:
            print(e)

        completions.append(if_complete)
        print('.....done! ')
        print('Elapsed time: {}'.format(time() - start) + '\n')


# specify the excel to process
# 1. verify if the member status is valid
# 3. store the QR code
if __name__ == "__main__":
    info_path = sys.argv[1]
    process_info(info_path)
