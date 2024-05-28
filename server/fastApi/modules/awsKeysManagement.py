import boto3
from botocore.exceptions import ClientError
import json


class SecretsManager:
    __instance = None

    @staticmethod
    def getInstance():
        if SecretsManager.__instance == None:
            SecretsManager()
        return SecretsManager.__instance

    def __init__(self, region_name="ap-south-1"):
        # Initialize the Secrets Manager client once when the class instance is created
        client = boto3.session.Session().client(
            service_name="secretsmanager", region_name=region_name
        )
        SecretsManager.__instance = client


def getAwsSecretKey():
    get_secret_value_response = SecretsManager.getInstance().get_secret_value(
        SecretId="DialogGPT"
    )
    secret = json.loads(get_secret_value_response["SecretString"])
    return secret


def get_firebase_config():
    secrets = getAwsSecretKey()
    return secrets["firebase"]


def get_stripe_config(env="prod"):
    secrets = getAwsSecretKey()
    return secrets["stripe"][env]


def get_email_config():
    secrets = getAwsSecretKey()
    return secrets["email"]


def get_currency_layer_api_key():
    secrets = getAwsSecretKey()
    return secrets["currency_layer_api_key"]


def get_jwt_secret_config():
    secrets = getAwsSecretKey()
    return {
        "secret_key": secrets["jwt_secret_key"],
        "algorithm": secrets["jwt_algorith"],
    }


def get_openai_api_key():
    secrets = getAwsSecretKey()
    return secrets["openai_api_key"]


def get_pinecone_config():
    secrets = getAwsSecretKey()
    return secrets["pinecone"]
