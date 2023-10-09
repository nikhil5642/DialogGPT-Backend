import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

email_sender = "nikhil@dialogGPT.io"
email_password = "ntuvvxepsiyovdrq"

def sendWelcomeEmail(receiver):
    subject = "Welcome To DialogGPT!"

    body = """
Hello there,<br><br>

🎉 A huge welcome to the DialogGPT community! 🎉<br><br>

We're thrilled to have you on board. Here's why joining us is one of the best decisions you've made:

🤖 <b>State-of-the-Art Conversations</b>: With DialogGPT, you're not just using any chatbot. You're experiencing the future of communication, powered by cutting-edge AI technology.<br><br>

🚀 <b>Limitless Possibilities</b>: Whether you're looking to enhance customer support, boost sales, or simply have a chat, DialogGPT is here to revolutionize the way you interact.<br><br>

💡 <b>Continuous Improvements</b>: We're always evolving. With regular updates and features, your experience will only get better over time.<br><br>

🤝 <b>We're Here for You</b>: Got questions? Need assistance? Our dedicated support team is always ready to help.<br><br>

Remember, every great conversation starts with a simple 'Hello'. So, go ahead, strike a chat with DialogGPT and witness the magic unfold.<br><br>

Cheers to new beginnings and endless conversations! 🥂<br><br>

Warm regards,<br>
Nikhil Agrawal<br>
Founder, DialogGPT<br><br>
"""

    sendEmail(email_sender, receiver, subject, body, msg_type='html')

def sendEmail(sender, receiver, subject, msg, msg_type='plain'):
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(email_sender, email_password)
    
    msg_mime = MIMEMultipart('alternative')
    msg_mime['Subject'] = subject
    msg_mime['From'] = f"DialogGPT <{email_sender}>"
    msg_mime['To'] = str(receiver)
    
    data = MIMEText(msg, msg_type)
    msg_mime.attach(data)
    
    server.send_message(msg_mime)
    server.quit()


if __name__ == "__main__":
    # print("send email")
    sendWelcomeEmail("nikhilagrawal5642@gmail.com")
    sendWelcomeEmail("support@dialoggpt.io")
    