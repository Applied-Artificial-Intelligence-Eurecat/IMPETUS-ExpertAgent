import yaml
import os

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        content = yaml.safe_load(file)
    return content

def get_title_from_document(document):
    name_path = document.source.metadata["source"].split("/")[-1]
    return os.path.splitext(name_path)[0]