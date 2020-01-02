# Built-In Modules
import os
import requests
import json

# 3rd Party Modules
import fedmsg
import fedmsg.config
import jinja2
from rhmsg.activemq.consumer import AMQConsumer
from rhmsg.activemq.consumer import ReceiverHandler

# Local Modules
from sync2jira.mailer import send_mail
from sync2jira.main import load_config

# Global Variables
handlers = [
    'repotracker.container.tag.updated'
]
TOKEN = os.environ['TOKEN']
ENDPOINT = os.environ['ENDPOINT']
NAMESPACE = os.environ['NAMESPACE']
CERT = os.environ['CERT']
KEY = os.environ['KEY']
CA_CERTS = os.environ['CA_CERTS']

def main():
    """
    Main function to start listening
    """
    # Load in config
    config = fedmsg.config.load_config()
    config['validate_signatures'] = False

    # Start listening
    print('Starting up CD service...')
    for _, _, topic, msg in fedmsg.tail_messages(mute=True, **config):
        # Extract out suffix
        suffix = ".".join(topic.split('.')[3:])
        if suffix not in handlers:
            continue

        # If its for sync2jira and pushed into master, update our tag
        if msg['msg']['reponame'] == 'sync2jira' and msg['msg']['tag'] == 'master':
            response, ret = update_tag()
            if response is False:
                print("Failed to update our Image Stream. Sending failure email...")
                # Send a failure email
                report_email(type='failure', ret=ret)
            else:
                # Send a success email
                print("Succeeded to update our Image Stream. Sending failure email...")
                report_email(type='success', ret=ret)


def update_tag():
    """
    Update OpenShift image when fedmsg topic comes in.

    :rtype (Bool, response):
    :return: (Indication if we updated out image on OpenShift, API call response)
    """
    # Make our put call
    ret = requests.put(f'https://{ENDPOINT}/apis/image.openshift.io/v1/namespaces/{NAMESPACE}/imagestreamtags/sync2jira-stage:latest',
                       headers=create_header(),
                       data=json.dumps({
                           "kind": "ImageStreamTag",
                           "apiVersion": "image.openshift.io/v1",
                           "metadata": {
                               "name": "sync2jira-stage:latest",
                               "namespace": "sync2jira-stage",
                               "creationTimestamp": None},
                           "tag": {
                               "name": "",
                               "annotations": None,
                               "from": {
                                   "kind": "DockerImage",
                                   "name": "quay.io/redhat-aqe/sync2jira:latest"
                               },
                               "generation": 0,
                               "importPolicy": {},
                               "referencePolicy": {
                                   "type": "Source"
                               }
                           },
                           "generation": 0,
                           "lookupPolicy": {
                               "local": False
                           },
                           "image": {
                               "metadata": {
                                   "creationTimestamp": None
                               },
                               "dockerImageMetadata": None,
                               "dockerImageLayers": None
                           }
                       }))
    if ret.status_code == 200:
        return True, ret
    else:
        return False, ret


def report_email(type, ret):
    """
    Helper function to alert admins in case of failure.

    :param Dict config: Config dict for JIRA
    :param response ret: Response from API call
    """
    # Load in the Sync2Jira config
    config = load_config()

    # Email our admins with the traceback
    templateLoader = jinja2.FileSystemLoader(searchpath='usr/local/src/sync2jira')
    templateEnv = jinja2.Environment(loader=templateLoader)

    # Load in the type of template
    if type is 'failure':
        template = templateEnv.get_template('failure_template.jinja')
        html_text = template.render(response=ret.json())
    elif type is 'success':
        template = templateEnv.get_template('success_template.jinja')
        html_text = template.render()

    # Get admin information
    admins = []
    for admin in config['sync2jira']['admins']:
        admins.append(list(admin.values())[0])

    # Send mail
    send_mail(recipients=admins,
              cc=None,
              subject=f"Sync2Jira Build Image Update Status: {type}!",
              text=html_text)


def create_header():
    """
    Helper function to create default header
    :rtype Dict:
    :return: Default header
    """
    return {
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

if __name__ == '__main__':
    update_tag()
    # main()
