"""
Model, that represents test case for a code task.
"""

from django.db import models
import re
import json

class Test(models.Model):
    """
    Model that holds input & output for a program
    """
    pk : models.IntegerField = models.IntegerField(primary_key=True, unique=True)
    test_input: models.TextField = models.TextField()
    test_output: models.TextField = models.TextField()

    # TODO: checkers

    def __init__(self, test_input: str, test_output: str):
        self.set_input
        self.set_output

    def set_input(self, test_input: str) -> None:
        self.test_input = test_input

    def set_output(self, test_output: str) -> None:
        self.test_output = test_output