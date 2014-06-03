import boto
import logging
from boto.s3.key import Key
from boto.exception import S3ResponseError
from pprint import pprint
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import pymongo

''' helpful documentation on boto: http://docs.pythonboto.org/en/latest/ref/ec2.html#boto.ec2.instance.Reservation '''
class BotoWrapper:
    AWS_ACCESS_KEY_ID = ""
    AWS_SECRET_ACCESS_KEY = ""
    logger = None

    def __init__(self, access_key, secret_key, logfile='botowrapper.log'):
        if None == access_key or None == secret_key:
            raise Exception('botowrapper requires initialization with AWS keys!')

        self.AWS_ACCESS_KEY_ID = access_key;
        self.AWS_SECRET_ACCESS_KEY = secret_key;
        #setup logging
        logger = logging.getLogger('botowrapper')
        #logfile = logging.FileHandler('/var/log/delivery_export_redshift/export.log')
        logfile = logging.FileHandler(logfile)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        logfile.setFormatter(formatter)
        logger.addHandler(logfile)
        logger.setLevel(logging.INFO)
        self.logger = logger

    def connectSES(self):
        ses_conn = boto.connect_ses(self.AWS_ACCESS_KEY_ID,self.AWS_SECRET_ACCESS_KEY)
        #self.logger.info("Connecting to SES")
        return ses_conn

    def connectEC2(self):
        ec2_conn = boto.connect_ec2(self.AWS_ACCESS_KEY_ID,self.AWS_SECRET_ACCESS_KEY)
        #self.logger.info("Connecting to EC2")
        return ec2_conn

    def connectELB(self):
        ec2_lb_conn = boto.connect_elb(self.AWS_ACCESS_KEY_ID,self.AWS_SECRET_ACCESS_KEY)
        #self.logger.info("Connecting to ELB")
        return ec2_lb_conn

    def connectS3(self):
        s3_conn = boto.connect_s3(self.AWS_ACCESS_KEY_ID,self.AWS_SECRET_ACCESS_KEY)
        #self.logger.info("Connecting to S3")
        return s3_conn

    def getELBList(self,nameFilter):
        ec2_lb_conn = self.connectELB()
        if (None == nameFilter):
            elbs = ec2_lb_conn.get_all_load_balancers()
        else:
            elbs = ec2_lb_conn.get_all_load_balancers(load_balancer_names=nameFilter)

        return elbs

    def getInstancesInElb(self,elbName):
        if None == elbName:
            self.logger.error("Call to getInstancesInELB without elb name")
            raise Exception('getInstancesInElb requires an ELBName')

        listOfElbs = self.getELBList(nameFilter=elbName)
        for elb in listOfElbs:
            serverIdList = elb.instances

        IdListOfServers = []
        for svrid in serverIdList:
            IdListOfServers.append(svrid.id)

        ec2_conn = self.connectEC2()
        reservationList = ec2_conn.get_all_instances(instance_ids=IdListOfServers)
        instanceList = []
        for reservation in reservationList:
            for instance in reservation.instances:
                instanceList.append(instance)

        return instanceList

    #SES
    def generateMessage(self, message, subject, fromUser, receipents, replyto, attachment, filename):
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = fromUser
        msg['Reply-to'] = replyto
        msg['To'] = receipents

        if not None==attachment:
            msg.preamble = 'Multipart massage.\n'
            # This is the binary part(The Attachment):
            part = MIMEApplication(open(attachment,"rb").read())
            part.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(part)

        part = MIMEText(message)
        msg.attach(part)

        return msg



    ''' receipents should be a comma delimited string
        attachment is the actual file directory to file
        filename is a string of the filename'''
    def sendEmail(self,message, subject, receipents, fromUser, replyto, attachment, filename):
        message = self.generateMessage(message, subject, fromUser, receipents, replyto, attachment, filename)
        conn = self.connectSES()
        conn.send_raw_email(message.as_string())

    ''' getInstancesbyTag(self, field, filter) where filter = string based on field '''
    def getInstancesbyTag(self, field, filter):
        if None == filter or None == field:
            return None

        newfilter = {"tag:"+field:filter}
        conn = self.connectEC2()
        result = conn.get_all_instances(filters=newfilter)

        return result

    def getAllTags(self):
        conn = self.connectEC2()
        result = conn.get_all_tags()
        return result

    def getAllInstances(self):
        conn = self.connectEC2()
        result = conn.get_all_instances()
        return result

    def getInstance(self, id):
        conn = self.connectEC2()
        resultlist = conn.get_all_instances(instance_ids=[id])
        result = []
        for reservations in resultlist:
            for instances in reservations.instances:
                result.append(instances)

        return result

    def percent_complete(self, complete=0, total=0):
        self.logger.info('Copying file to S3, %s of %s bytes (%s%%) uploaded.' % (complete, total, ((complete*100/total))))

    def uploadFileToS3(self,bucket, file, filename):
        self.logger.info('Copying file ' + file + ' to S3 bucket '+ bucket)
        '''
        uploadFileToS3 :
        bucket == string name of the S3 Bucket,
        file is the string location of the full fire directory, ex. /tmp/filename.file
        filename = string of the actual filename
        '''
        conn = self.connectS3()
        try:
            s3bucket = conn.get_bucket(bucket)
            key = Key(s3bucket)
            key.key=filename

            key.set_contents_from_filename(filename=file,headers=None,replace=True,cb=self.percent_complete,num_cb=10)

            #done? return true
            return True
        except (S3ResponseError, BaseException) as e:
            self.logger.error("Error sending file to S3"+str(e.__class__) + "::"+str(e.message) + "::" + str(e.args))
            raise BaseException("Error sending file to S3"+str(e.__class__) + "::"+str(e.message) + "::" + str(e.args))

        return False

    ## mongo level functions
    def connectToServer(self, server=None, listOfServers=[], rsName=None, **options):
        '''
        connectToServer will take either a single server (server) or list of servers (listOfServers) and return you either
        1. pymongo connection
        2. replicaset connection
        The readPreferences are : PRIMARY_PREFERRED,SECONDARY_PREFERRED documented here: http://api.mongodb.org/python/current/api/pymongo/
        '''
        conn = None


        try:
            if not (None == server):
                # single server, go
                conn = pymongo.MongoClient(server, 27017)
            else:
                if len(listOfServers) > 0:
                    # go replicaset!
                    if None == rsName:
                        raise Exception("PyMongo requires replicaset name (rsName) to be specified if this is a replicaset connection")

                    conn = pymongo.MongoReplicaSetClient(hosts_or_uri=listOfServers, replicaSet=rsName, **options)
        except (BaseException) as e:
            raise Exception("Unable to get PyMongo Connection " +str(e.__class__) + "::"+str(e.message) + "::" + str(e.args))

        return conn

    def getRSServerList(self, rsName=None, **options):
        '''
        getRSSErverList returns a list of servers within a replicaset
        '''
        resvs = self.getInstancesbyTag('Name',rsName)
        instanceList = []
        for res in resvs:
            for instance in res.instances:
                if instance.public_dns_name.strip() != '':
                    instanceList.append(instance.public_dns_name)

        return instanceList

    def connectToRs(self, rsName=None, **options):
        '''
         connectToRs is a convenience method that will search ec2 for servers in that replicaset and establish a connection.
        :rtype : pymongo::Connection
        :param rsName:
        :**options: Example: read_preference=read_preferences.ReadPreference.SECONDARY_PREFERRED
        '''

        instanceList = self.getRSServerList(rsName, options)

        connection = pymongo.MongoReplicaSetClient(hosts_or_uri=",".join(instanceList), replicaSet=rsName.replace('*',''), w=1, **options )
        return connection

__author__ = 'warren chang :: https://github.com/changzone/botowrapper'
