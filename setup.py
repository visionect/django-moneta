import os

from setuptools import setup, find_packages

VERSION = '0.1'

if __name__ == '__main__':
    setup(
        name = 'django-moneta',
        version = VERSION,
        description = "Django app for Moneta eTerminal API.",
        long_description = open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
        author = 'Visionect d.o.o., Matevž Mihalič',
        author_email = 'matevz.mihalic@visionect.si',
        url = 'https://github.com/visionect/django-moneta',
        keywords = "moneta django api eterminal",
        license = 'MIT',
        packages = find_packages(),
        classifiers = (
            'Development Status :: 4 - Beta',
            'Environment :: Web Environment',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Framework :: Django',
        ),
        install_requires = (
            'Django>=1.3',
            'pysimplesoap>=1.08b',
            'python-nss>=0.12'
        )
    )