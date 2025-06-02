import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def path(file_path):
    return os.path.join(root_dir, *file_path.split("/"))


def read_file(file_path):
    with open(path(file_path), "r", encoding="utf-8") as file:
        contents = "".join(file.readlines())

    return contents


def write_file(file_path, text):
    with open(path(file_path), "w", encoding="utf-8") as file:
        file.writelines(text)


def remove_file(file_name):
    try:
        os.remove(file_name)
    except (FileNotFoundError, PermissionError):
        return