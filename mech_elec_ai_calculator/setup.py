from setuptools import setup, find_packages

setup(
    name='mech_elec_ai_calculator',
    version='1.0.0',
    description='机电AI自动算量+三维建模+OpenHuman审核系统',
    author='MechElecAI',
    packages=find_packages(),
    install_requires=[
        'pydantic>=2.0',
        'ezdxf>=1.0',
        'PyMuPDF>=1.23',
        'opencv-python>=4.8',
        'numpy>=1.26',
        'pyyaml>=6.0',
        'requests>=2.31',
        'openpyxl>=3.1',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0',
            'pytest-cov>=4.0',
            'flake8>=6.0',
        ],
        'yolo': [
            'ultralytics>=8.0',
            'pytesseract>=0.3.10',
        ],
    },
    entry_points={
        'console_scripts': [
            'mech-elec-calc=main:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3.10',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
)