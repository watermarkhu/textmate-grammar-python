:py:mod:`textmate_grammar.handler`
==================================

.. py:module:: textmate_grammar.handler

.. autodoc2-docstring:: textmate_grammar.handler
   :allowtitles:

Module Contents
---------------

Classes
~~~~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`ContentHandler <textmate_grammar.handler.ContentHandler>`
     - .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler
          :summary:

Data
~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`POS <textmate_grammar.handler.POS>`
     - .. autodoc2-docstring:: textmate_grammar.handler.POS
          :summary:

API
~~~

.. py:data:: POS
   :canonical: textmate_grammar.handler.POS
   :value: None

   .. autodoc2-docstring:: textmate_grammar.handler.POS

.. py:class:: ContentHandler(source: str)
   :canonical: textmate_grammar.handler.ContentHandler

   .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler.__init__

   .. py:attribute:: notLookForwardEOL
      :canonical: textmate_grammar.handler.ContentHandler.notLookForwardEOL
      :value: 'compile(...)'

      .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler.notLookForwardEOL

   .. py:method:: from_path(file_path: pathlib.Path)
      :canonical: textmate_grammar.handler.ContentHandler.from_path
      :classmethod:

      .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler.from_path

   .. py:method:: next(pos: textmate_grammar.handler.POS, step: int = 1) -> textmate_grammar.handler.POS
      :canonical: textmate_grammar.handler.ContentHandler.next

      .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler.next

   .. py:method:: prev(pos: textmate_grammar.handler.POS, step: int = 1) -> textmate_grammar.handler.POS
      :canonical: textmate_grammar.handler.ContentHandler.prev

      .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler.prev

   .. py:method:: range(start: textmate_grammar.handler.POS, close: textmate_grammar.handler.POS) -> list[textmate_grammar.handler.POS]
      :canonical: textmate_grammar.handler.ContentHandler.range

      .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler.range

   .. py:method:: chars(start: textmate_grammar.handler.POS, close: textmate_grammar.handler.POS) -> dict[textmate_grammar.handler.POS, str]
      :canonical: textmate_grammar.handler.ContentHandler.chars

      .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler.chars

   .. py:method:: read_pos(start_pos: textmate_grammar.handler.POS, close_pos: textmate_grammar.handler.POS, skip_newline: bool = True) -> str
      :canonical: textmate_grammar.handler.ContentHandler.read_pos

      .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler.read_pos

   .. py:method:: read_line(pos: textmate_grammar.handler.POS) -> str
      :canonical: textmate_grammar.handler.ContentHandler.read_line

      .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler.read_line

   .. py:method:: read(start_pos: textmate_grammar.handler.POS, length: int = 1, skip_newline: bool = True) -> str
      :canonical: textmate_grammar.handler.ContentHandler.read

      .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler.read

   .. py:method:: search(pattern: onigurumacffi._Pattern, starting: textmate_grammar.handler.POS, boundary: textmate_grammar.handler.POS | None = None, greedy: bool = False, **kwargs) -> tuple[onigurumacffi._Match | None, tuple[textmate_grammar.handler.POS, textmate_grammar.handler.POS] | None]
      :canonical: textmate_grammar.handler.ContentHandler.search

      .. autodoc2-docstring:: textmate_grammar.handler.ContentHandler.search
