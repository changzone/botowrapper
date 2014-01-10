botowrapper
===========
This is a simple wrapper around the python BOTO aws library.  
So far I've wrapped:
SES - Simple Email Service // added ability to add a binary file attachment
EC2 - Lookup instances and load balancer configurations
      Can also create mongo db connections to servers
S3 - Copy files up to S3

Make sure to add this to your import paths prior to referencing this module

#assumes your file path is ./botowrapper contains the BotoWrapper.py file
sys.path.append('./botowrapper')
from BotoWrapper import BotoWrapper


Examples of use:

    To init the class
    botowrapper = BotoWrapper(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY)

    if you want to get a list of instances in an ELB
	serverList = botowrapper.getInstancesInElb('<ELBNAME') 

    if you want to send an email
    botowrapper.sendEmail(message="Some Message! "+str(e.message),
                                          subject="SOME SUBJECGT!",fromUser="user@place.com",
                                          replyto="user@place.com",receipents="user@place.com",attachment=None,filename=None)
