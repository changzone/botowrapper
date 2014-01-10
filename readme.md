botowrapper
===========

Simple wrapper class around the python BOTO AWS library
This wrapper covers:
SES - Simple Email Service :: Sends emails and allows for local attachments
S3 - File Copy to S3
EC2 - List and connect to servers in EC2 and LIST servers behind ELBs
    - open MongoDB connections to EC2 servers based on hostname lookup


Install
======
Make sure to add this to your import paths prior to referencing this module

assumes your file path is ./botowrapper contains the BotoWrapper.py file
sys.path.append('./botowrapper')
from BotoWrapper import BotoWrapper


Examples of use
===============
    To init the class
    botowrapper = BotoWrapper(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY)

    if you want to get a list of instances in an ELB
    serverList = botowrapper.getInstancesInElb('RecorderLB')

    if you want to send an email
    botowrapper.sendEmail(message="Delivery Check Failed! "+str(e.message),
                                          subject="STATUS Update!",fromUser="user@place.com",
                                          replyto="user@place.com",receipents="user@place.com",attachment=None,filename=None)
