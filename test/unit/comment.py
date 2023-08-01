import unittest
from sphinx_matlab.parser import Parser
from sphinx_matlab.tmlanguage import TMLIST


class TestComment(unittest.TestCase):
    def setUpClass(cls):
        Parser(TMLIST["repository"]["comment_block"], key="comment_block")
        cls.parser = Parser(TMLIST["repository"]["comments"], key="comments")
