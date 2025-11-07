Installation
============

Requirements
------------

* Python 3.8 or higher

Basic Installation
------------------

Install the core library without dependencies:

.. code-block:: bash

    pip install sqlmeta

Optional Dependencies
---------------------

SQLAlchemy Support
~~~~~~~~~~~~~~~~~~

For SQLAlchemy integration:

.. code-block:: bash

    pip install sqlmeta[sqlalchemy]

Pydantic Support
~~~~~~~~~~~~~~~~

For Pydantic model generation:

.. code-block:: bash

    pip install sqlmeta[pydantic]

Alembic Support
~~~~~~~~~~~~~~~

For Alembic migration integration:

.. code-block:: bash

    pip install sqlmeta[alembic]

All Optional Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~

Install all optional dependencies at once:

.. code-block:: bash

    pip install sqlmeta[all]

Development Installation
------------------------

For development with testing and code quality tools:

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/cmodiano/sqlmeta.git
    cd sqlmeta

    # Create virtual environment
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

    # Install in development mode
    pip install -e ".[dev,all]"

Verifying Installation
----------------------

To verify that sqlmeta is installed correctly:

.. code-block:: python

    import sqlmeta
    print(sqlmeta.__version__)

To check which optional dependencies are available:

.. code-block:: python

    from sqlmeta.adapters import __all__
    print("Available adapters:", __all__)
