****************************
Schema for Schema Definition
****************************

Schema Schema
=============

This defines how a schema should be created.. 

.. code-block:: python

  {'fields': [
      {
        'name': pythonidentifier,
        'title': short_string,
        'description': long_string,
        'type': schema_type,
        'validator': validatish_validator,
      },
    ]
  }

name
----

This will be used in couchdb and in python so only valid python identifiers can be used. It will also be used in html forms. 

title & description
-------------------

Used as meta data (for instance, title will override the name for the label in formish)

type
----

Any schemaish types. We should probably use the same format as the type itself (i.e. String, DateParts) in order to keep consistency. 

.. note:: should type default to string - I think so personally

validator
---------

This is a single validator or combination.. This will be eval'd but checked to be valid first (i.e. no arbitrary execution of python). e.g.

.. code-block:: python

  'validator': 'Required()'

  # or

  'validator': 'Any(Integer(), Float())'


Adding Widgets
==============

widgets are added as below

.. code-block:: python

  {'fields': [
      {
        'name': pythonidentifier,
        'title': short_string,
        'description': long_string,
        'type': schema_type,
        'validator': validatish_validator,
        'widget': {
            'type': widget_type,
            .... any keyword or positional arguments, use arg name for positionals ...

            }

          }
      },
    ]
  }

Some examples
=============

Here are a few examples 

.. code-block:: python

  {'fields': [
      {
        'name': 'title',
        'widget': {
            'type': 'SelectChoice',
            'options': [('mr','Mr'),('mrs','Mrs'),('miss','Miss')],
            'none_option': ('None','--select your title--'),
            }

      },
      {
        'name': 'first_name',
        'title': 'First Name',
        'validator': 'Required()'
      },
      {
        'name': 'interests',
        'type': 'Sequence(String())',
        'widget': {
            'type': 'CheckboxMultiChoice',
            'options': ['golf','quantum physics','knitting'],
            }
      },

    ]
  }


Using with Couchish
==================

If we want to include references to other objects, we need to make sure we can point to them.. e.g. The select for title in the first part 

here is a simple example of a persona title (e.g. Mr, Mrs)

.. code-block:: python

  {'fields': [
      {
        'name': 'title',
        'type': 'ref',
        'view': {
          'name': '/title/all',
          },


      },

    ]
  }

.. code-block:: python

  {'views': [

    {
      'name': '/title/all',
    }
  ],
  
  }

.. code-block:: python

  {'views': [

    {
      'name': '/title/all',
      'source_attrs': 'name',
    }
  ],
  
  }

Representing a Book - Author relationship
-----------------------------------------

Here is a more complicated version where we have a book and an author .. The books author uses a view to pull in the reference. This creates dictionary structure for the ``author`` that I've shown at the end of this section.


``book``

.. code-block:: python

  {'fields': [
      {
        'name': 'author',
        'type': 'ref',
        'view': 'author_name', 
      },
      {
        'name': 'title',
      },
    ]
  }


``author``

.. code-block:: python


  {'fields': [
      {
        'name': 'title',
        'widget': {
            'type': 'SelectChoice',
            'options': [('mr','Mr'),('mrs','Mrs'),('miss','Miss')],
            'none_option': ('None','--select your title--'),
            }
      },
      {
        'name': 'first_name',
        'title': 'First Name',
        'validator': 'Required()'
      },
      {
        'name': 'last_name',
        'title': 'Last Name',
        'validator': 'Required()'
      },
      {
        'name': 'birthday',
        'type': 'Date()',
      },

    ]
  }


``views``

.. code-block:: python

  {'views': [

    {
      'name': 'author_name',
      'url': '/author/name_by_id',
      'map' : ' function(doc) { emit(doc._id, {first_name: doc.first_name, last_name: doc.last_name}); }',
      'uses': ['first_name','last_name'],
    }
  ],
  
  }


An example book json structure
------------------------------

.. code-block:: json

  { 
    "author": {
       "_ref": "42e29d907e04087a8ab1e40cc467a259",
       "first_name": "Isaac",
       "last_name": "Asimov",
       }
    "title": "I, Robot",
  }

  {
    "title": "Mr",
    "first_name": "Isaac",
    "last_name": "Asimov",
    "birthday": "1936-09-01",
  }




And the yaml data that builds it 
--------------------------------

.. code-block:: yaml

    author:
      fields:
        - name: first_name

        - name: last_name

        - name: birthday
          type: date

    book:
      fields:
        - name: title

        - name: author
          type: ref
          view: author_name
      
    views: 
      - name: author_name
        url: /author/name_by_id
        map : function(doc) { emit(doc._id, {first_name: doc.first_name, last_name: doc.last_name}); }
        uses: [first_name, last_name]




And the yaml data that builds it 
--------------------------------

.. code-block:: yaml

    author:
      fields:
        - name: first_name

        - name: last_name
          viewby: True

        - name: birthday
          type: date

    book:
      fields:
        - name: title

        - name: author
          type: ref
          view: author_name
      
    views: 
      - name: author_name
        url: /author/name_by_id
        map : function(doc) { emit(doc._id, {first_name: doc.first_name, last_name: doc.last_name}); }
        uses: [first_name, last_name]
