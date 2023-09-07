from setuptools import setup, find_packages

setup(
    name='niagads-pylib',
    version='0.1.0',    
    description='libraries and utils in support of NIAGADS projects',
    url='https://github.com/NIAGADS/niagads-pylib',
    author='fossilfriend',
    author_email='egreenfest@gmail.com',
    license='GNU GPLv3',
    packages=find_packages(), # ['niagads', 'niagads.filer', 'niagads.utils'],
    install_requires=['openpyxl'],
    entry_points ={
        'console_scripts': [
               'variant_annotator = niagads.scripts.variant_annotator:main'
        ]
        },
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU GPLv3',  
        'Operating System :: POSIX :: Linux',        
        'Programming Language :: Python :: 3.6.x',
    ],
)
