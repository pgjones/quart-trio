from quart.formparser import FormDataParser

from .datastructures import TrioFileStorage


class TrioFormDataParser(FormDataParser):
    file_storage_class = TrioFileStorage
