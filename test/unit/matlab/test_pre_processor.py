import logging

from textmate_grammar.grammars.matlab import MatlabGrammar

matlab_grammar = MatlabGrammar(remove_line_continuations=True)


logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)


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

    result = matlab_grammar.pre_process(input_string)
    assert result == output_string, "Incorrect pre-processed string"
