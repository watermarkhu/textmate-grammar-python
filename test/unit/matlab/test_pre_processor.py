import logging

from textmate_grammar.grammars import matlab


logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)

processor = matlab.PreProcessor()

def test_preprocessor():

    input_string = "".join([
        "function [outputArg1,...\n",
        "   outputArg2]...\n"
        "   = myFunction(inputArg1, ... Comment string \n"
        "   inputArg2)\n",
        "end\n"
        ""
    ])

    output_string = "function [outputArg1,outputArg2]= myFunction(inputArg1, inputArg2)\nend\n"

    result = processor.process(input_string)
    assert result == output_string, "Incorrect pre-processed string"
    