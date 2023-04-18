from quart.formparser import FormDataParser

from quart_trio.datastructures import TrioFileStorage


class TrioFormDataParser(FormDataParser):
    file_storage_class = TrioFileStorage
