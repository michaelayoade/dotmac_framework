# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath('../isp-framework/src')
sys.path.insert(0, os.path.abspath('../management-platform/app')
sys.path.insert(0, os.path.abspath('../shared')
sys.path.insert(0, os.path.abspath('..')

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'DotMac Platform'
copyright = f'{datetime.now().year}, DotMac Technologies'
author = 'DotMac Development Team'
release = '1.0.0'
version = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.githubpages',
    'sphinx.ext.doctest',
    'sphinx.ext.duration',
    'sphinx_rtd_theme',
    'myst_parser',
    'sphinx_copybutton',
    'sphinxcontrib.mermaid',
    'sphinx_tabs.tabs',
    'sphinx_design',
]

# Add support for Markdown files
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# Napoleon settings for Google and NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
    'show-inheritance': True,
    'inherited-members': True,
}

autodoc_typehints = 'description'
autodoc_typehints_format = 'short'
# STRATEGIC: Only mock what is LITERALLY IMPOSSIBLE to replicate
# Based on comprehensive import analysis - fixed security and dependency issues
autodoc_mock_imports = [
    # 🚫 IMPOSSIBLE: External APIs (cost money, need real credentials)
    'stripe',          # Payment processing: Real money transactions
    'twilio',          # SMS/Voice: Real charges per message  
    'boto3',           # AWS: Creates real cloud resources
    'aiobotocore',     # AWS async client
    'botocore',        # AWS core client
    'azure',           # Microsoft Azure APIs
    'google-cloud',    # Google Cloud Platform APIs
    'minio',           # S3-compatible storage (needs server)
    
    # 🚫 IMPOSSIBLE: Network hardware (needs physical equipment)
    'pysnmp',          # SNMP: Requires routers/switches/modems
    'netmiko',         # SSH: Network device configuration
    'napalm',          # Multi-vendor network automation
    'paramiko',        # SSH: Server access (security risk in docs)
    
    # 🚫 IMPOSSIBLE: System automation (needs target infrastructure)  
    'ansible',         # Server provisioning & configuration
    'ansible-runner',  # Playbook execution environment
    'docker',          # Container management (needs Docker daemon)
    'kubernetes',      # Container orchestration (needs K8s cluster)
    
    # 📦 HEAVY: Optional observability (mock for performance)
    'opentelemetry',
    'opentelemetry-api', 
    'opentelemetry-sdk',
    'opentelemetry-instrumentation',
    'opentelemetry-instrumentation-fastapi',
    'opentelemetry-instrumentation-sqlalchemy', 
    'opentelemetry-instrumentation-redis',
    'opentelemetry-instrumentation-celery',
    'opentelemetry-instrumentation-httpx',
    'prometheus-client',
    
    # 🔒 SECURITY: Mock potentially dangerous packages found in analysis
    'psycopg2',        # PostgreSQL driver (needs database)
    'psycopg2-binary', # PostgreSQL binary driver
    'redis',           # Redis client (needs Redis server)
    'aioredis',        # Async Redis client
    'celery',          # Task queue (needs broker)
]

# 🎯 STRATEGY: Everything else gets installed for production-grade docs
# Including: Redis, PostgreSQL, MongoDB via Docker Compose

# Everything else gets INSTALLED for production-grade documentation

# Enable better error handling for import issues
autodoc_mock_imports_strict = False

# Intersphinx mapping to external documentation
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'fastapi': ('https://fastapi.tiangolo.com', None),
    'sqlalchemy': ('https://docs.sqlalchemy.org/en/20/', None),
    'pydantic': ('https://docs.pydantic.dev/2.8/', None),
    'redis': ('https://redis-py.readthedocs.io/en/latest/', None),
}

# The master toctree document
master_doc = 'index'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '**/.git', '**/node_modules']

# The name of the Pygments (syntax highlighting) style to use
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing
todo_include_todos = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False,
}

# Add custom CSS
html_static_path = ['_static']
html_css_files = [
    'custom.css',
]

# The name of an image file (relative to this directory) to place at the top
# of the sidebar
# html_logo = '_static/logo.png'

# The name of an image file (relative to this directory) to use as a favicon
# html_favicon = '_static/favicon.ico'

# Output file base name for HTML help builder
htmlhelp_basename = 'DotMacDoc'

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    'papersize': 'letterpaper',
    'pointsize': '10pt',
    'preamble': r'''
\usepackage{charter}
\usepackage[defaultsans]{lato}
\usepackage{inconsolata}
''',
    'fncychap': '\\usepackage[Bjornstrup]{fncychap}',
    'printindex': '\\footnotesize\\raggedright\\printindex',
}

# Grouping the document tree into LaTeX files
latex_documents = [
    (master_doc, 'DotMac.tex', 'DotMac Platform Documentation',
     'DotMac Development Team', 'manual'),
]

# -- Options for manual page output ------------------------------------------

man_pages = [
    (master_doc, 'dotmac', 'DotMac Platform Documentation',
     [author], 1)
]

# -- Options for Texinfo output ----------------------------------------------

texinfo_documents = [
    (master_doc, 'DotMac', 'DotMac Platform Documentation',
     author, 'DotMac', 'Enterprise ISP Management Platform',
     'Miscellaneous'),
]

# -- Options for Epub output -------------------------------------------------

epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# A list of files that should not be packed into the epub file
epub_exclude_files = ['search.html']

# -- Extension configuration -------------------------------------------------

# MyST parser configuration for Markdown support
myst_enable_extensions = [
    "deflist",
    "tasklist",
    "html_image",
    "colon_fence",
    "smartquotes",
    "replacements",
    "linkify",
    "substitution",
]

myst_heading_anchors = 3
myst_footnote_transition = True
myst_dmath_double_inline = True
myst_enable_checkboxes = True
myst_substitutions = {
    "version": version,
    "release": release,
}
