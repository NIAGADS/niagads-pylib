from setuptools import setup

setup(
    name='niagads-pylib',
    version='0.1.0',    
    description='libraries and utils in support of NIAGADS projects',
    url='https://github.com/NIAGADS/niagads-pylib',
    author='fossilfriend',
    author_email='egreenfest@gmail.com',
    license='GNU GPLv3',
    packages=['filer', 'utils'],
    install_requires=['openpyxl'],
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU GPLv3',  
        'Operating System :: POSIX :: Linux',        
        'Programming Language :: Python :: 3.6.x',
    ],
)
