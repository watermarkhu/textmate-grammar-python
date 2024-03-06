:py:mod:`textmate_grammar.cache`
================================

.. py:module:: textmate_grammar.cache

.. autodoc2-docstring:: textmate_grammar.cache
   :allowtitles:

Module Contents
---------------

Classes
~~~~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`TextmateCache <textmate_grammar.cache.TextmateCache>`
     - .. autodoc2-docstring:: textmate_grammar.cache.TextmateCache
          :summary:
   * - :py:obj:`SimpleCache <textmate_grammar.cache.SimpleCache>`
     - .. autodoc2-docstring:: textmate_grammar.cache.SimpleCache
          :summary:
   * - :py:obj:`ShelveCache <textmate_grammar.cache.ShelveCache>`
     - .. autodoc2-docstring:: textmate_grammar.cache.ShelveCache
          :summary:

Functions
~~~~~~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`init_cache <textmate_grammar.cache.init_cache>`
     - .. autodoc2-docstring:: textmate_grammar.cache.init_cache
          :summary:

Data
~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`CACHE_DIR <textmate_grammar.cache.CACHE_DIR>`
     - .. autodoc2-docstring:: textmate_grammar.cache.CACHE_DIR
          :summary:
   * - :py:obj:`CACHE <textmate_grammar.cache.CACHE>`
     - .. autodoc2-docstring:: textmate_grammar.cache.CACHE
          :summary:

API
~~~

.. py:data:: CACHE_DIR
   :canonical: textmate_grammar.cache.CACHE_DIR
   :value: 'resolve(...)'

   .. autodoc2-docstring:: textmate_grammar.cache.CACHE_DIR

.. py:class:: TextmateCache
   :canonical: textmate_grammar.cache.TextmateCache

   Bases: :py:obj:`typing.Protocol`

   .. autodoc2-docstring:: textmate_grammar.cache.TextmateCache

   .. py:method:: cache_valid(filepath: pathlib.Path) -> bool
      :canonical: textmate_grammar.cache.TextmateCache.cache_valid

      .. autodoc2-docstring:: textmate_grammar.cache.TextmateCache.cache_valid

   .. py:method:: load(filepath: pathlib.Path) -> textmate_grammar.elements.ContentElement
      :canonical: textmate_grammar.cache.TextmateCache.load

      .. autodoc2-docstring:: textmate_grammar.cache.TextmateCache.load

   .. py:method:: save(filePath: pathlib.Path, element: textmate_grammar.elements.ContentElement) -> None
      :canonical: textmate_grammar.cache.TextmateCache.save

      .. autodoc2-docstring:: textmate_grammar.cache.TextmateCache.save

.. py:class:: SimpleCache()
   :canonical: textmate_grammar.cache.SimpleCache

   Bases: :py:obj:`textmate_grammar.cache.TextmateCache`

   .. autodoc2-docstring:: textmate_grammar.cache.SimpleCache

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.cache.SimpleCache.__init__

   .. py:method:: cache_valid(filepath: pathlib.Path) -> bool
      :canonical: textmate_grammar.cache.SimpleCache.cache_valid

      .. autodoc2-docstring:: textmate_grammar.cache.SimpleCache.cache_valid

   .. py:method:: load(filepath: pathlib.Path) -> textmate_grammar.elements.ContentElement
      :canonical: textmate_grammar.cache.SimpleCache.load

      .. autodoc2-docstring:: textmate_grammar.cache.SimpleCache.load

   .. py:method:: save(filepath: pathlib.Path, element: textmate_grammar.elements.ContentElement) -> None
      :canonical: textmate_grammar.cache.SimpleCache.save

      .. autodoc2-docstring:: textmate_grammar.cache.SimpleCache.save

.. py:class:: ShelveCache()
   :canonical: textmate_grammar.cache.ShelveCache

   Bases: :py:obj:`textmate_grammar.cache.TextmateCache`

   .. autodoc2-docstring:: textmate_grammar.cache.ShelveCache

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.cache.ShelveCache.__init__

   .. py:method:: cache_valid(filepath: pathlib.Path) -> bool
      :canonical: textmate_grammar.cache.ShelveCache.cache_valid

      .. autodoc2-docstring:: textmate_grammar.cache.ShelveCache.cache_valid

   .. py:method:: load(filepath: pathlib.Path) -> textmate_grammar.elements.ContentElement
      :canonical: textmate_grammar.cache.ShelveCache.load

      .. autodoc2-docstring:: textmate_grammar.cache.ShelveCache.load

   .. py:method:: save(filepath: pathlib.Path, element: textmate_grammar.elements.ContentElement) -> None
      :canonical: textmate_grammar.cache.ShelveCache.save

      .. autodoc2-docstring:: textmate_grammar.cache.ShelveCache.save

.. py:data:: CACHE
   :canonical: textmate_grammar.cache.CACHE
   :type: textmate_grammar.cache.TextmateCache
   :value: 'SimpleCache(...)'

   .. autodoc2-docstring:: textmate_grammar.cache.CACHE

.. py:function:: init_cache(type: str = 'simple') -> textmate_grammar.cache.TextmateCache
   :canonical: textmate_grammar.cache.init_cache

   .. autodoc2-docstring:: textmate_grammar.cache.init_cache
