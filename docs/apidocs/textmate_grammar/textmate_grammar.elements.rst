:py:mod:`textmate_grammar.elements`
===================================

.. py:module:: textmate_grammar.elements

.. autodoc2-docstring:: textmate_grammar.elements
   :allowtitles:

Module Contents
---------------

Classes
~~~~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`Capture <textmate_grammar.elements.Capture>`
     - .. autodoc2-docstring:: textmate_grammar.elements.Capture
          :summary:
   * - :py:obj:`ContentElement <textmate_grammar.elements.ContentElement>`
     - .. autodoc2-docstring:: textmate_grammar.elements.ContentElement
          :summary:
   * - :py:obj:`ContentBlockElement <textmate_grammar.elements.ContentBlockElement>`
     - .. autodoc2-docstring:: textmate_grammar.elements.ContentBlockElement
          :summary:

Data
~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`TOKEN_DICT <textmate_grammar.elements.TOKEN_DICT>`
     - .. autodoc2-docstring:: textmate_grammar.elements.TOKEN_DICT
          :summary:

API
~~~

.. py:data:: TOKEN_DICT
   :canonical: textmate_grammar.elements.TOKEN_DICT
   :value: None

   .. autodoc2-docstring:: textmate_grammar.elements.TOKEN_DICT

.. py:class:: Capture(handler: textmate_grammar.handler.ContentHandler, pattern: textmate_grammar.handler.Pattern, matching: textmate_grammar.handler.Match, parsers: dict[int, textmate_grammar.parser.GrammarParser], starting: tuple[int, int], boundary: tuple[int, int], key: str = '', **kwargs)
   :canonical: textmate_grammar.elements.Capture

   .. autodoc2-docstring:: textmate_grammar.elements.Capture

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.elements.Capture.__init__

   .. py:method:: dispatch() -> list[textmate_grammar.elements.Capture | textmate_grammar.elements.ContentElement]
      :canonical: textmate_grammar.elements.Capture.dispatch

      .. autodoc2-docstring:: textmate_grammar.elements.Capture.dispatch

.. py:class:: ContentElement(token: str, grammar: dict, content: str, characters: dict[textmate_grammar.handler.POS, str], children: list[textmate_grammar.elements.Capture | textmate_grammar.elements.ContentElement] | None = None)
   :canonical: textmate_grammar.elements.ContentElement

   .. autodoc2-docstring:: textmate_grammar.elements.ContentElement

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.elements.ContentElement.__init__

   .. py:property:: children
      :canonical: textmate_grammar.elements.ContentElement.children
      :type: list[textmate_grammar.elements.ContentElement]

      .. autodoc2-docstring:: textmate_grammar.elements.ContentElement.children

   .. py:method:: find(tokens: str | list[str], start_tokens: str | list[str] = '', hide_tokens: str | list[str] = '', stop_tokens: str | list[str] = '', depth: int = -1, attribute: str = '_subelements', stack: list[str] | None = None) -> typing.Generator[tuple[textmate_grammar.elements.ContentElement, list[str]], None, None]
      :canonical: textmate_grammar.elements.ContentElement.find

      .. autodoc2-docstring:: textmate_grammar.elements.ContentElement.find

   .. py:method:: findall(tokens: str | list[str], start_tokens: str | list[str] = '', hide_tokens: str | list[str] = '', stop_tokens: str | list[str] = '', depth: int = -1, attribute: str = '_subelements') -> list[tuple[textmate_grammar.elements.ContentElement, list[str]]]
      :canonical: textmate_grammar.elements.ContentElement.findall

      .. autodoc2-docstring:: textmate_grammar.elements.ContentElement.findall

   .. py:method:: to_dict(depth: int = -1, all_content: bool = False, **kwargs) -> dict
      :canonical: textmate_grammar.elements.ContentElement.to_dict

      .. autodoc2-docstring:: textmate_grammar.elements.ContentElement.to_dict

   .. py:method:: flatten() -> list[tuple[tuple[int, int], str, list[str]]]
      :canonical: textmate_grammar.elements.ContentElement.flatten

      .. autodoc2-docstring:: textmate_grammar.elements.ContentElement.flatten

   .. py:method:: print(flatten: bool = False, depth: int = -1, all_content: bool = False, **kwargs) -> None
      :canonical: textmate_grammar.elements.ContentElement.print

      .. autodoc2-docstring:: textmate_grammar.elements.ContentElement.print

.. py:class:: ContentBlockElement(begin: list[textmate_grammar.elements.Capture | textmate_grammar.elements.ContentElement] | None = None, end: list[textmate_grammar.elements.Capture | textmate_grammar.elements.ContentElement] | None = None, **kwargs)
   :canonical: textmate_grammar.elements.ContentBlockElement

   Bases: :py:obj:`textmate_grammar.elements.ContentElement`

   .. autodoc2-docstring:: textmate_grammar.elements.ContentBlockElement

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.elements.ContentBlockElement.__init__

   .. py:property:: begin
      :canonical: textmate_grammar.elements.ContentBlockElement.begin
      :type: list[textmate_grammar.elements.ContentElement]

      .. autodoc2-docstring:: textmate_grammar.elements.ContentBlockElement.begin

   .. py:property:: end
      :canonical: textmate_grammar.elements.ContentBlockElement.end
      :type: list[textmate_grammar.elements.ContentElement]

      .. autodoc2-docstring:: textmate_grammar.elements.ContentBlockElement.end

   .. py:method:: to_dict(depth: int = -1, all_content: bool = False, **kwargs) -> dict
      :canonical: textmate_grammar.elements.ContentBlockElement.to_dict

      .. autodoc2-docstring:: textmate_grammar.elements.ContentBlockElement.to_dict
