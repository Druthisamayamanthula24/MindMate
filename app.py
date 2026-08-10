import streamlit as st
import sqlite3
import hashlib
import random
import time
import datetime as dt
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

# ============================================================
# MINDMATE - SMART STUDY COMPANION
# Final structure:
# Login -> Dashboard -> Study Planner -> Tomorrow's Plan ->
# Adaptive Quiz -> Doubt Chatbot -> Coding Tracker ->
# Stress Monitor -> Puzzle Zone -> Analytics -> Settings -> Logout
#
# Core loop:
# Semester subjects -> Topic -> Study timer -> Unique quiz ->
# Performance -> Weak topic -> Tomorrow's plan -> Analytics
# ============================================================

st.set_page_config(
    page_title="MindMate - Smart Study Companion",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CONFIG / CONSTANTS
# ============================================================
DB_PATH = Path("mindmate.db")

ALL_SUBJECTS = [
    "Data Structures", "Python", "COA", "Modern Physics", "CRTC",
    "DBMS", "DAE", "ASE", "AI", "C++", "P&S", "ADSAA"
]

TOPICS = {
    "Data Structures": [
        "Arrays",
        "Stacks & Queues",
        "Linked Lists",
        "Trees",
        "Graphs"
    ],
    "Python": [
        "Functions",
        "OOP",
        "Exceptions",
        "File Handling",
        "Recursion"
    ],
    "COA": [
        "CPU Organization",
        "ALU",
        "Cache Memory",
        "DMA",
        "Memory Hierarchy"
    ],
    "Modern Physics": [
        "Quantum Theory",
        "Photoelectric Effect",
        "Dual Nature",
        "Atoms",
        "Nuclear Physics"
    ],
    "CRTC": [
        "Aptitude",
        "Logical Reasoning",
        "Verbal Ability",
        "Coding Basics",
        "Communication"
    ],
    "DBMS": [
        "ER Model",
        "SQL",
        "Normalization",
        "Transactions",
        "Indexing"
    ],
    "DAE": [
        "Differential Equations",
        "Laplace Transform",
        "Fourier Series",
        "Partial Derivatives",
        "Applications"
    ],
    "ASE": [
        "Software Engineering",
        "SDLC",
        "Requirements",
        "Testing",
        "Agile"
    ],
    "AI": [
        "AI Basics",
        "Search",
        "Machine Learning",
        "Neural Networks",
        "Ethics"
    ],
    "C++": [
        "Syntax & STL",
        "OOP",
        "Pointers",
        "Templates",
        "STL Algorithms"
    ],
    "P&S": [
        "Probability",
        "Random Variables",
        "Distributions",
        "Statistics",
        "Hypothesis Testing"
    ],
    "ADSAA": [
        "Advanced Data Structures",
        "Algorithms",
        "Complexity",
        "Dynamic Programming",
        "Greedy Algorithms"
    ]
}

QUESTION_BANK = {'Data Structures': {'Arrays': [('ds-arr-01',
                                 'What is the first index of a zero-based array?',
                                 ['0', '1', '-1', 'Depends'],
                                 '0'),
                                ('ds-arr-02',
                                 'Which array operation is generally O(1) when the index is known?',
                                 ['Random access', 'Insertion at beginning', 'Deletion at beginning', 'Linear search'],
                                 'Random access'),
                                ('ds-arr-03',
                                 'Which structure stores elements in contiguous memory in the usual array model?',
                                 ['Array', 'Linked list', 'Tree', 'Graph'],
                                 'Array'),
                                ('ds-arr-04',
                                 'For an array of n elements, linear search has worst-case time complexity:',
                                 ['O(1)', 'O(log n)', 'O(n)', 'O(n²)'],
                                 'O(n)')],
                     'Stacks & Queues': [('ds-sq-01',
                                          'A stack follows which principle?',
                                          ['FIFO', 'LIFO', 'Random', 'Priority'],
                                          'LIFO'),
                                         ('ds-sq-02',
                                          'Which operation adds an item to a stack?',
                                          ['Push', 'Pop', 'Peek', 'Dequeue'],
                                          'Push'),
                                         ('ds-sq-03',
                                          'A normal queue follows which principle?',
                                          ['LIFO', 'FIFO', 'Random', 'Divide and conquer'],
                                          'FIFO'),
                                         ('ds-sq-04',
                                          'Which structure is commonly used for breadth-first search?',
                                          ['Stack', 'Queue', 'Heap', 'Hash table'],
                                          'Queue')],
                     'Linked Lists': [('ds-ll-01',
                                       'A singly linked-list node normally contains data and:',
                                       ['A next pointer', 'Two stacks', 'A queue', 'A matrix'],
                                       'A next pointer'),
                                      ('ds-ll-02',
                                       'Insertion at the head of a linked list can be done in:',
                                       ['O(1)', 'O(log n)', 'O(n)', 'O(n²)'],
                                       'O(1)'),
                                      ('ds-ll-03',
                                       'Which linked list has pointers in both directions?',
                                       ['Singly', 'Doubly', 'Circular singly only', 'Static'],
                                       'Doubly'),
                                      ('ds-ll-04',
                                       "A circular linked list's last node points to:",
                                       ['NULL', 'The first node', 'Itself always', 'The middle node'],
                                       'The first node')],
                     'Trees': [('ds-tr-01',
                                'Which traversal of a binary search tree gives sorted order?',
                                ['Preorder', 'Inorder', 'Postorder', 'Level order'],
                                'Inorder'),
                               ('ds-tr-02',
                                'A tree with n nodes has how many edges?',
                                ['n', 'n-1', 'n+1', '2n'],
                                'n-1'),
                               ('ds-tr-03',
                                'A node with no children is called a:',
                                ['Root', 'Leaf', 'Parent', 'Sibling'],
                                'Leaf'),
                               ('ds-tr-04',
                                'Which structure is a self-balancing binary search tree?',
                                ['AVL tree', 'Stack', 'Queue', 'Hash table'],
                                'AVL tree')],
                     'Graphs': [('ds-gr-01',
                                 'A graph is primarily made of:',
                                 ['Vertices and edges', 'Rows and columns', 'Keys and values', 'Stacks and queues'],
                                 'Vertices and edges'),
                                ('ds-gr-02',
                                 'Which traversal normally uses a queue?',
                                 ['BFS', 'DFS', 'Inorder', 'Postorder'],
                                 'BFS'),
                                ('ds-gr-03',
                                 'Which traversal can be implemented using a stack?',
                                 ['BFS', 'DFS', 'Level order', 'None'],
                                 'DFS'),
                                ('ds-gr-04',
                                 'An edge from a vertex to itself is called a:',
                                 ['Loop', 'Leaf', 'Root', 'Bridge'],
                                 'Loop')]},
 'Python': {'Functions': [('py-fn-01',
                           'Which keyword defines a function in Python?',
                           ['func', 'def', 'function', 'define'],
                           'def'),
                          ('py-fn-02',
                           'Which keyword sends a value back from a function?',
                           ['send', 'return', 'back', 'yieldonly'],
                           'return'),
                          ('py-fn-03',
                           'What does *args collect?',
                           ['Keyword arguments', 'Positional arguments', 'Modules', 'Exceptions'],
                           'Positional arguments'),
                          ('py-fn-04',
                           'What does **kwargs collect?',
                           ['Keyword arguments', 'Positional arguments', 'Lists only', 'Files'],
                           'Keyword arguments')],
            'OOP': [('py-oop-01', 'An object is an instance of a:', ['Class', 'Loop', 'File', 'Module only'], 'Class'),
                    ('py-oop-02',
                     'Which concept lets a class derive from another class?',
                     ['Inheritance', 'Iteration', 'Hashing', 'Recursion'],
                     'Inheritance'),
                    ('py-oop-03',
                     'Which method commonly initializes a Python object?',
                     ['__start__', '__init__', 'initiate', 'constructor_only'],
                     '__init__'),
                    ('py-oop-04',
                     'Hiding internal implementation details is called:',
                     ['Encapsulation', 'Sorting', 'Parsing', 'Iteration'],
                     'Encapsulation')],
            'Exceptions': [('py-ex-01',
                            'Which keyword starts a block that may raise an exception?',
                            ['try', 'catch', 'error', 'handle'],
                            'try'),
                           ('py-ex-02',
                            'Which keyword handles an exception?',
                            ['catch', 'except', 'error', 'handle'],
                            'except'),
                           ('py-ex-03',
                            'Which block normally runs whether an exception occurs or not?',
                            ['try', 'except', 'finally', 'raise'],
                            'finally'),
                           ('py-ex-04',
                            'Which keyword explicitly raises an exception?',
                            ['throw', 'raise', 'except', 'error'],
                            'raise')],
            'File Handling': [('py-file-01', 'Which mode opens a file for reading?', ['r', 'w', 'a', 'x'], 'r'),
                              ('py-file-02',
                               'Which mode writes to a file and truncates existing content?',
                               ['r', 'w', 'a', 'x'],
                               'w'),
                              ('py-file-03', 'Which mode appends to an existing file?', ['r', 'w', 'a', 'x'], 'a'),
                              ('py-file-04',
                               'Which pattern automatically closes a file?',
                               ['with open()', 'if open()', 'for open()', 'open only'],
                               'with open()')],
            'Recursion': [('py-rec-01',
                           'A recursive function needs a:',
                           ['Base case', 'Database', 'Class only', 'GUI'],
                           'Base case'),
                          ('py-rec-02',
                           'Recursive calls are tracked on the:',
                           ['Call stack', 'Queue', 'Heap only', 'Hash table'],
                           'Call stack'),
                          ('py-rec-03',
                           'Without a reachable base case, recursion may cause:',
                           ['Infinite recursion', 'Sorting', 'Caching', 'Compilation'],
                           'Infinite recursion'),
                          ('py-rec-04',
                           'Recursion solves a problem by reducing it to:',
                           ['Smaller instances of the same problem', 'Only loops', 'Only files', 'Only classes'],
                           'Smaller instances of the same problem')]},
 'COA': {'CPU Organization': [('coa-cpu-01',
                               'Which unit directs the operations of the CPU?',
                               ['Control Unit', 'ALU', 'Cache', 'RAM'],
                               'Control Unit'),
                              ('coa-cpu-02',
                               'The CPU component that performs arithmetic and logic is the:',
                               ['ALU', 'CU', 'Register file only', 'DMA'],
                               'ALU'),
                              ('coa-cpu-03',
                               'Which is a fast storage location inside the CPU?',
                               ['Register', 'Hard disk', 'Optical disk', 'Printer'],
                               'Register'),
                              ('coa-cpu-04',
                               'The usual first phase of instruction processing is:',
                               ['Fetch', 'Print', 'Sort', 'Compile'],
                               'Fetch')],
         'ALU': [('coa-alu-01',
                  'ALU stands for:',
                  ['Arithmetic Logic Unit', 'Array Logic Unit', 'Application Link Unit', 'Arithmetic Link Utility'],
                  'Arithmetic Logic Unit'),
                 ('coa-alu-02', 'Which is a logical operation?', ['AND', 'Fetch', 'Store', 'Decode'], 'AND'),
                 ('coa-alu-03',
                  'Which is an arithmetic operation?',
                  ['Addition', 'Jump', 'Fetch', 'Decode'],
                  'Addition'),
                 ('coa-alu-04', 'The ALU is a part of the:', ['CPU', 'Keyboard', 'Monitor', 'Disk'], 'CPU')],
         'Cache Memory': [('coa-cache-01',
                           'Cache is generally located between:',
                           ['CPU and main memory', 'Keyboard and monitor', 'Disk and printer', 'Compiler and source'],
                           'CPU and main memory'),
                          ('coa-cache-02',
                           'A cache hit means the requested data is:',
                           ['Found in cache', 'Deleted', 'Only on disk', 'Unavailable'],
                           'Found in cache'),
                          ('coa-cache-03',
                           'Which cache mapping allows a block to map to any cache line?',
                           ['Fully associative', 'Direct', 'Fixed', 'Sequential'],
                           'Fully associative'),
                          ('coa-cache-04',
                           'Cache improves performance mainly by reducing:',
                           ['Average memory access time', 'Program size', 'Keyboard latency', 'Screen resolution'],
                           'Average memory access time')],
         'DMA': [('coa-dma-01',
                  'DMA stands for:',
                  ['Direct Memory Access', 'Data Memory Allocation', 'Digital Memory Access', 'Direct Module Access'],
                  'Direct Memory Access'),
                 ('coa-dma-02',
                  'DMA is mainly used for transfers between:',
                  ['I/O and memory', 'ALU and CU', 'Monitor and keyboard', 'ROM and printer'],
                  'I/O and memory'),
                 ('coa-dma-03',
                  'The component that manages DMA transfers is the:',
                  ['DMA controller', 'Compiler', 'ALU', 'Cache'],
                  'DMA controller'),
                 ('coa-dma-04',
                  'DMA reduces the need for the CPU to handle:',
                  ['Every byte of a bulk transfer', 'All instructions', 'All interrupts', 'All arithmetic'],
                  'Every byte of a bulk transfer')],
         'Memory Hierarchy': [('coa-mh-01',
                               'Which is generally the fastest storage level?',
                               ['Registers', 'RAM', 'SSD', 'Hard disk'],
                               'Registers'),
                              ('coa-mh-02',
                               'As memory becomes faster, cost per bit generally:',
                               ['Increases', 'Decreases to zero', 'Never changes', 'Becomes irrelevant'],
                               'Increases'),
                              ('coa-mh-03',
                               'Main memory is commonly implemented using:',
                               ['RAM', 'Keyboard', 'Monitor', 'Printer'],
                               'RAM'),
                              ('coa-mh-04',
                               'Which level is larger but slower than cache?',
                               ['Main memory', 'Register', 'ALU', 'Control unit'],
                               'Main memory')]},
 'Modern Physics': {'Quantum Theory': [('phy-q-01',
                                        'Planck proposed that energy is emitted or absorbed in:',
                                        ['Quanta', 'Only continuous waves', 'Circles', 'Matrices only'],
                                        'Quanta'),
                                       ('phy-q-02',
                                        'Photon energy is given by:',
                                        ['E = hf', 'E = mc', 'E = IR', 'E = Pt only'],
                                        'E = hf'),
                                       ('phy-q-03', "Planck's constant has SI unit:", ['J·s', 'N', 'W', 'C'], 'J·s'),
                                       ('phy-q-04',
                                        'The quantum description of light is associated with:',
                                        ['Photons', 'Only sound waves', 'Only electrons', 'Only nuclei'],
                                        'Photons')],
                    'Photoelectric Effect': [('phy-pe-01',
                                              'The minimum frequency needed for photoemission is called:',
                                              ['Threshold frequency',
                                               'Clock frequency',
                                               'Beat frequency',
                                               'Resonant current'],
                                              'Threshold frequency'),
                                             ('phy-pe-02',
                                              'Increasing light intensity above threshold generally increases:',
                                              ['Photoelectric current',
                                               'Work function',
                                               'Threshold frequency',
                                               'Electron mass'],
                                              'Photoelectric current'),
                                             ('phy-pe-03',
                                              'Maximum photoelectron kinetic energy depends mainly on:',
                                              ['Light frequency', 'Only intensity', 'Wire length', 'Room temperature'],
                                              'Light frequency'),
                                             ('phy-pe-04',
                                              'The photoelectric effect supports the:',
                                              ['Particle nature of light',
                                               'Only sound nature',
                                               'Fluid nature of light',
                                               'Heat-only model'],
                                              'Particle nature of light')],
                    'Dual Nature': [('phy-dn-01',
                                     'de Broglie proposed that matter has:',
                                     ['Wave nature', 'Only charge', 'Only heat', 'No motion'],
                                     'Wave nature'),
                                    ('phy-dn-02',
                                     'Electron diffraction demonstrates:',
                                     ['Matter waves', 'Only classical motion', 'Sound waves', 'Thermal radiation'],
                                     'Matter waves'),
                                    ('phy-dn-03',
                                     'The de Broglie wavelength is inversely proportional to:',
                                     ['Momentum', 'Mass only', 'Time only', 'Temperature'],
                                     'Momentum'),
                                    ('phy-dn-04',
                                     'A photon has zero rest mass but carries:',
                                     ['Energy and momentum', 'Only charge', 'Only rest mass', 'No momentum'],
                                     'Energy and momentum')],
                    'Atoms': [('phy-at-01',
                               "Bohr's model introduced:",
                               ['Quantized energy levels', 'Continuous energy only', 'No electrons', 'No nucleus'],
                               'Quantized energy levels'),
                              ('phy-at-02',
                               'An emitted photon is produced when an electron moves to a:',
                               ['Lower energy level', 'Higher level only', 'Random level', 'Nuclear state only'],
                               'Lower energy level'),
                              ('phy-at-03',
                               'The nucleus contains:',
                               ['Protons and neutrons', 'Only electrons', 'Only photons', 'Only atoms'],
                               'Protons and neutrons'),
                              ('phy-at-04',
                               'Atomic spectra provide evidence for:',
                               ['Discrete energy levels',
                                'Only continuous energy',
                                'No quantization',
                                'Classical-only atoms'],
                               'Discrete energy levels')],
                    'Nuclear Physics': [('phy-nu-01',
                                         'E = mc² relates:',
                                         ['Mass and energy',
                                          'Charge and current',
                                          'Force and pressure',
                                          'Time and distance'],
                                         'Mass and energy'),
                                        ('phy-nu-02',
                                         'Radioactivity is the spontaneous transformation of:',
                                         ['Unstable nuclei', 'Stable wires', 'Photons only', 'Atoms in all states'],
                                         'Unstable nuclei'),
                                        ('phy-nu-03',
                                         'The atomic number equals the number of:',
                                         ['Protons', 'Neutrons', 'Nucleons', 'Electrons plus neutrons'],
                                         'Protons'),
                                        ('phy-nu-04',
                                         'Nuclear fission is the:',
                                         ['Splitting of a heavy nucleus',
                                          'Combining of two light nuclei',
                                          'Emission of visible light',
                                          'Removal of electrons'],
                                         'Splitting of a heavy nucleus')]},
 'CRTC': {'Aptitude': [('crtc-ap-01', 'What is 25% of 200?', ['25', '40', '50', '75'], '50'),
                       ('crtc-ap-02', 'A 10% increase on 100 gives:', ['105', '110', '120', '90'], '110'),
                       ('crtc-ap-03',
                        "If a job takes 10 days for one person, one day's work is:",
                        ['1/10', '1/5', '10', '1/20'],
                        '1/10'),
                       ('crtc-ap-04', 'The average of 10 and 20 is:', ['10', '15', '20', '30'], '15')],
          'Logical Reasoning': [('crtc-lr-01',
                                 'If all A are B and all B are C, then:',
                                 ['All A are C', 'No A are C', 'Some A are not C', 'None'],
                                 'All A are C'),
                                ('crtc-lr-02',
                                 'A sequence puzzle mainly tests:',
                                 ['Pattern recognition', 'Typing', 'Drawing', 'Color choice'],
                                 'Pattern recognition'),
                                ('crtc-lr-03', 'Which does not belong: 2, 4, 6, 9?', ['2', '4', '6', '9'], '9'),
                                ('crtc-lr-04',
                                 'If today is Monday, what day is 3 days later?',
                                 ['Tuesday', 'Wednesday', 'Thursday', 'Friday'],
                                 'Thursday')],
          'Verbal Ability': [('crtc-va-01',
                              "Choose the synonym of 'rapid':",
                              ['Slow', 'Quick', 'Weak', 'Late'],
                              'Quick'),
                             ('crtc-va-02',
                              "Choose the antonym of 'ancient':",
                              ['Old', 'Modern', 'Historic', 'Past'],
                              'Modern'),
                             ('crtc-va-03',
                              "A word that means 'a place where books are kept' is:",
                              ['Library', 'Laboratory', 'Gallery', 'Factory'],
                              'Library'),
                             ('crtc-va-04',
                              'Choose the grammatically correct sentence:',
                              ['She go to class.', 'She goes to class.', 'She going class.', 'She gone class.'],
                              'She goes to class.')],
          'Coding Basics': [('crtc-cb-01',
                             'Which structure stores key-value pairs in many languages?',
                             ['Map/Dictionary', 'Stack only', 'Queue only', 'Array index only'],
                             'Map/Dictionary'),
                            ('crtc-cb-02',
                             'A loop is mainly used to:',
                             ['Repeat instructions', 'Delete a program', 'Compile hardware', 'Encrypt a monitor'],
                             'Repeat instructions'),
                            ('crtc-cb-03',
                             'A conditional statement is used to:',
                             ['Make decisions', 'Store files only', 'Draw graphs only', 'Create hardware'],
                             'Make decisions'),
                            ('crtc-cb-04',
                             'Which is a common algorithmic approach?',
                             ['Divide and conquer', 'Print and erase', 'Click and drag', 'Copy and paste'],
                             'Divide and conquer')],
          'Communication': [('crtc-com-01',
                             'Effective communication requires:',
                             ['Clear message and active listening', 'Only speaking', 'Only writing', 'No feedback'],
                             'Clear message and active listening'),
                            ('crtc-com-02',
                             'Feedback helps a speaker:',
                             ['Understand how the message was received',
                              'Avoid all questions',
                              'Increase noise',
                              'Remove context'],
                             'Understand how the message was received'),
                            ('crtc-com-03',
                             'Non-verbal communication includes:',
                             ['Body language', 'Only code', 'Only equations', 'Database keys'],
                             'Body language'),
                            ('crtc-com-04',
                             'A concise message is usually:',
                             ['Clear and brief', 'Long and repetitive', 'Ambiguous', 'Incomplete'],
                             'Clear and brief')]},
 'DBMS': {'ER Model': [('db-er-01',
                        'An entity represents a:',
                        ['Distinct real-world object', 'SQL keyword only', 'Transaction log', 'File extension'],
                        'Distinct real-world object'),
                       ('db-er-02',
                        'An attribute describes an:',
                        ['Entity property', 'Index page only', 'SQL transaction', 'Network packet'],
                        'Entity property'),
                       ('db-er-03',
                        'A relationship represents an association between:',
                        ['Entities', 'Only attributes', 'Only indexes', 'Only queries'],
                        'Entities'),
                       ('db-er-04',
                        'A primary key should uniquely identify:',
                        ['Each row/entity instance', 'Every database', 'Every table name', 'Every query'],
                        'Each row/entity instance')],
          'SQL': [('db-sql-01',
                   'Which SQL command retrieves rows?',
                   ['SELECT', 'FETCHFILE', 'GETROW', 'READ'],
                   'SELECT'),
                  ('db-sql-02', 'Which clause filters rows?', ['WHERE', 'ORDER', 'GROUP', 'HAVINGONLY'], 'WHERE'),
                  ('db-sql-03', 'Which command adds a new row?', ['INSERT', 'ADDROW', 'PUT', 'CREATE'], 'INSERT'),
                  ('db-sql-04',
                   'Which command modifies existing rows?',
                   ['UPDATE', 'CHANGE', 'MODIFYTABLE', 'EDIT'],
                   'UPDATE')],
          'Normalization': [('db-norm-01',
                             'Normalization mainly reduces:',
                             ['Data redundancy', 'CPU clock speed', 'Network bandwidth', 'Screen size'],
                             'Data redundancy'),
                            ('db-norm-02',
                             'First Normal Form requires values to be:',
                             ['Atomic', 'Encrypted', 'Sorted', 'Duplicated'],
                             'Atomic'),
                            ('db-norm-03',
                             'A functional dependency describes a relationship between:',
                             ['Attributes', 'Tables only', 'Files only', 'Queries only'],
                             'Attributes'),
                            ('db-norm-04',
                             'Normalization can help reduce:',
                             ['Update anomalies', 'Keyboard errors', 'CPU temperature', 'Display resolution'],
                             'Update anomalies')],
          'Transactions': [('db-tx-01',
                            "The 'A' in ACID stands for:",
                            ['Atomicity', 'Availability', 'Accuracy', 'Access'],
                            'Atomicity'),
                           ('db-tx-02',
                            "The 'C' in ACID stands for:",
                            ['Consistency', 'Concurrency', 'Compression', 'Compilation'],
                            'Consistency'),
                           ('db-tx-03',
                            "The 'I' in ACID stands for:",
                            ['Isolation', 'Indexing', 'Input', 'Iteration'],
                            'Isolation'),
                           ('db-tx-04',
                            "The 'D' in ACID stands for:",
                            ['Durability', 'Dependency', 'Data type', 'Distribution'],
                            'Durability')],
          'Indexing': [('db-ind-01',
                        'An index is primarily used to improve:',
                        ['Data retrieval speed', 'Table color', 'Password length', 'CPU instruction set'],
                        'Data retrieval speed'),
                       ('db-ind-02',
                        'A common tree used for database indexing is:',
                        ['B+ tree', 'AVL only', 'Expression tree only', 'Parse tree'],
                        'B+ tree'),
                       ('db-ind-03',
                        'An index can add overhead to:',
                        ['Insert/update operations', 'SELECT only', 'Display only', 'Compilation'],
                        'Insert/update operations'),
                       ('db-ind-04',
                        'A clustered index affects the physical/logical ordering of:',
                        ['Rows/data', 'Only SQL keywords', 'Only users', 'Only constraints'],
                        'Rows/data')]},
 'DAE': {'Differential Equations': [('dae-de-01',
                                     'The order of a differential equation is the highest order of:',
                                     ['Derivative present', 'Variable', 'Constant', 'Coefficient'],
                                     'Derivative present'),
                                    ('dae-de-02',
                                     'A first-order differential equation contains a highest derivative of:',
                                     ['First order', 'Second order', 'Third order', 'Zero only'],
                                     'First order'),
                                    ('dae-de-03',
                                     'The general solution of a first-order ODE usually contains:',
                                     ['One arbitrary constant',
                                      'No constants',
                                      'Two arbitrary constants always',
                                      'Only variables'],
                                     'One arbitrary constant'),
                                    ('dae-de-04',
                                     'An equation involving derivatives of a dependent variable is a:',
                                     ['Differential equation', 'Algebraic identity', 'Matrix only', 'Sequence'],
                                     'Differential equation')],
         'Laplace Transform': [('dae-lap-01',
                                'The Laplace transform is especially useful for solving:',
                                ['Differential equations', 'Only matrices', 'Only geometry', 'Only sorting'],
                                'Differential equations'),
                               ('dae-lap-02',
                                'The Laplace transform changes a function of time into a function of:',
                                ['Complex frequency variable s', 'Only x', 'Only y', 'Only angle'],
                                'Complex frequency variable s'),
                               ('dae-lap-03',
                                'The Laplace transform of 1 for t≥0 is:',
                                ['1/s', 's', '0', 'e^s'],
                                '1/s'),
                               ('dae-lap-04',
                                'Laplace methods are useful for incorporating:',
                                ['Initial conditions',
                                 'Only final conditions',
                                 'Only boundary labels',
                                 'Only graph colors'],
                                'Initial conditions')],
         'Fourier Series': [('dae-four-01',
                             'A Fourier series represents a periodic function using:',
                             ['Sines and cosines', 'Only polynomials', 'Only exponentials', 'Only matrices'],
                             'Sines and cosines'),
                            ('dae-four-02',
                             'The constant term in a Fourier series represents the:',
                             ['Average/DC component', 'Maximum frequency', 'Derivative', 'Error only'],
                             'Average/DC component'),
                            ('dae-four-03',
                             'Fourier series are commonly used to analyze:',
                             ['Periodic signals', 'Only databases', 'Only compilers', 'Only trees'],
                             'Periodic signals'),
                            ('dae-four-04',
                             'The Fourier coefficients depend on:',
                             ['Integrals over a period', 'Only one point', 'Only a constant', 'Only the final value'],
                             'Integrals over a period')],
         'Partial Derivatives': [('dae-pd-01',
                                  'A partial derivative differentiates with respect to:',
                                  ['One variable while holding others constant',
                                   'All variables at once',
                                   'No variable',
                                   'Only constants'],
                                  'One variable while holding others constant'),
                                 ('dae-pd-02',
                                  'For z=f(x,y), ∂z/∂x treats y as:',
                                  ['Constant', 'Zero always', 'Infinite', 'A function of x always'],
                                  'Constant'),
                                 ('dae-pd-03',
                                  'The symbol ∂ denotes a:',
                                  ['Partial derivative', 'Summation', 'Integral', 'Limit'],
                                  'Partial derivative'),
                                 ('dae-pd-04',
                                  'A function of two independent variables can have:',
                                  ['Partial derivatives with respect to both',
                                   'Only one derivative',
                                   'No derivatives',
                                   'Only a matrix'],
                                  'Partial derivatives with respect to both')],
         'Applications': [('dae-app-01',
                           'Differential equations are used to model:',
                           ['Rates of change', 'Only spelling', 'Only file formats', 'Only database keys'],
                           'Rates of change'),
                          ('dae-app-02',
                           'An RC circuit can be modeled using:',
                           ['A differential equation',
                            'Only a sorting algorithm',
                            'Only a pie chart',
                            'Only a database'],
                           'A differential equation'),
                          ('dae-app-03',
                           'A population growth model can use:',
                           ['Differential equations', 'Only SQL', 'Only stacks', 'Only Fourier coefficients'],
                           'Differential equations'),
                          ('dae-app-04',
                           'A solution to a differential equation should satisfy:',
                           ['The original equation and relevant conditions',
                            'Only a graph',
                            'Only an initial guess',
                            'Only the variable names'],
                           'The original equation and relevant conditions')]},
 'ASE': {'Software Engineering': [('ase-se-01',
                                   'Software engineering is primarily concerned with:',
                                   ['Systematic development of software',
                                    'Only typing code',
                                    'Only hardware design',
                                    'Only networking'],
                                   'Systematic development of software'),
                                  ('ase-se-02',
                                   'A software process model defines:',
                                   ['Activities and their relationships',
                                    'Only variable names',
                                    'Only test data',
                                    'Only database rows'],
                                   'Activities and their relationships'),
                                  ('ase-se-03',
                                   'Software maintenance occurs:',
                                   ['After deployment as needed',
                                    'Only before coding',
                                    'Only during requirements',
                                    'Never'],
                                   'After deployment as needed'),
                                  ('ase-se-04',
                                   'A key goal of software engineering is:',
                                   ['Quality and maintainability',
                                    'Maximum code length',
                                    'No documentation',
                                    'No testing'],
                                   'Quality and maintainability')],
         'SDLC': [('ase-sdlc-01',
                   'SDLC stands for:',
                   ['Software Development Life Cycle',
                    'System Data Logic Cycle',
                    'Software Design Link Code',
                    'System Development Logic Class'],
                   'Software Development Life Cycle'),
                  ('ase-sdlc-02',
                   'Which is commonly an early SDLC phase?',
                   ['Requirements', 'Deployment only', 'Retirement only', 'Debugging only'],
                   'Requirements'),
                  ('ase-sdlc-03',
                   'Testing is mainly used to:',
                   ['Find defects and verify behavior', 'Write requirements', 'Replace users', 'Design logos'],
                   'Find defects and verify behavior'),
                  ('ase-sdlc-04',
                   'Deployment means:',
                   ['Making software available for use',
                    'Deleting source code',
                    'Writing only tests',
                    'Collecting requirements'],
                   'Making software available for use')],
         'Requirements': [('ase-req-01',
                           'A functional requirement describes:',
                           ['What the system should do',
                            'Only system color',
                            'Only developer salary',
                            'Only hardware brand'],
                           'What the system should do'),
                          ('ase-req-02',
                           'A non-functional requirement describes:',
                           ['Quality/constraint characteristics',
                            'Only user names',
                            'Only database rows',
                            'Only algorithms'],
                           'Quality/constraint characteristics'),
                          ('ase-req-03',
                           'Requirements should be:',
                           ['Clear and verifiable', 'Ambiguous', 'Hidden', 'Contradictory'],
                           'Clear and verifiable'),
                          ('ase-req-04',
                           'A use case typically describes interaction between:',
                           ['Actor and system', 'Compiler and CPU', 'Database and printer', 'Keyboard and monitor'],
                           'Actor and system')],
         'Testing': [('ase-test-01',
                      'Unit testing focuses on:',
                      ['Individual components', 'The entire organization', 'Only UI colors', 'Only network cables'],
                      'Individual components'),
                     ('ase-test-02',
                      'Integration testing checks:',
                      ['Interactions between components', 'Only one variable', 'Only documentation', 'Only hardware'],
                      'Interactions between components'),
                     ('ase-test-03',
                      'Regression testing checks that changes did not:',
                      ['Break existing behavior', 'Improve code', 'Add features', 'Compile'],
                      'Break existing behavior'),
                     ('ase-test-04',
                      'A test case normally includes inputs and:',
                      ['Expected result', 'Only source code', 'Only screenshots', 'Only database schema'],
                      'Expected result')],
         'Agile': [('ase-ag-01',
                    'Agile emphasizes:',
                    ['Iterative delivery and feedback', 'One huge release only', 'No customer feedback', 'No testing'],
                    'Iterative delivery and feedback'),
                   ('ase-ag-02',
                    'A Scrum sprint is a:',
                    ['Time-boxed development iteration', 'Database table', 'Testing tool', 'Programming language'],
                    'Time-boxed development iteration'),
                   ('ase-ag-03',
                    'A product backlog contains:',
                    ['Prioritized work items', 'Only completed bugs', 'Only code binaries', 'Only user passwords'],
                    'Prioritized work items'),
                   ('ase-ag-04',
                    'Daily Scrum is intended for:',
                    ['Short team coordination', 'Long design documents', 'Customer billing', 'Database backups'],
                    'Short team coordination')]},
 'AI': {'AI Basics': [('ai-basic-01',
                       'AI aims to build systems that can perform tasks requiring:',
                       ['Intelligent behavior', 'Only arithmetic', 'Only storage', 'Only printing'],
                       'Intelligent behavior'),
                      ('ai-basic-02',
                       'Which is an AI application?',
                       ['Speech recognition', 'File renaming only', 'Keyboard lighting', 'Screen brightness'],
                       'Speech recognition'),
                      ('ai-basic-03',
                       'A knowledge representation stores:',
                       ['Information used for reasoning', 'Only images', 'Only passwords', 'Only source files'],
                       'Information used for reasoning'),
                      ('ai-basic-04',
                       'Machine learning is a subset of:',
                       ['Artificial Intelligence', 'Operating Systems', 'DBMS', 'Networking'],
                       'Artificial Intelligence')],
        'Search': [('ai-search-01',
                    'BFS explores a graph using a:',
                    ['Queue', 'Stack', 'Heap only', 'Database'],
                    'Queue'),
                   ('ai-search-02',
                    'DFS explores using a:',
                    ['Stack or recursion', 'Queue only', 'Hash table only', 'SQL'],
                    'Stack or recursion'),
                   ('ai-search-03',
                    'A heuristic is used to:',
                    ['Guide search toward promising states', 'Store passwords', 'Compile code', 'Encrypt disks'],
                    'Guide search toward promising states'),
                   ('ai-search-04',
                    'A* search combines path cost with:',
                    ['A heuristic estimate', 'Only depth', 'Only breadth', 'Only random choice'],
                    'A heuristic estimate')],
        'Machine Learning': [('ai-ml-01',
                              'Supervised learning uses:',
                              ['Labeled data', 'No data', 'Only rules', 'Only hardware'],
                              'Labeled data'),
                             ('ai-ml-02',
                              'Unsupervised learning works with:',
                              ['Unlabeled data', 'Only labeled outputs', 'Only rewards', 'Only SQL'],
                              'Unlabeled data'),
                             ('ai-ml-03',
                              'Classification predicts:',
                              ['Discrete classes', 'Only continuous values', 'Only database keys', 'Only text length'],
                              'Discrete classes'),
                             ('ai-ml-04',
                              'Overfitting means a model:',
                              ['Fits training data too closely and generalizes poorly',
                               'Cannot learn training data',
                               'Has no parameters',
                               'Always underfits'],
                              'Fits training data too closely and generalizes poorly')],
        'Neural Networks': [('ai-nn-01',
                             'A neuron computes a weighted sum followed by an:',
                             ['Activation function', 'SQL query', 'Index', 'Exception'],
                             'Activation function'),
                            ('ai-nn-02',
                             'Which activation is commonly used in hidden layers?',
                             ['ReLU', 'SELECT', 'FIFO', 'BFS'],
                             'ReLU'),
                            ('ai-nn-03',
                             'Backpropagation is used to:',
                             ['Compute gradients for learning', 'Store datasets', 'Sort arrays', 'Build indexes'],
                             'Compute gradients for learning'),
                            ('ai-nn-04',
                             'A neural network learns parameters by minimizing a:',
                             ['Loss function', 'File size', 'CPU temperature', 'Screen resolution'],
                             'Loss function')],
        'Ethics': [('ai-eth-01',
                    'AI bias can arise from:',
                    ['Biased data or design', 'Only faster CPUs', 'Only larger screens', 'Only network speed'],
                    'Biased data or design'),
                   ('ai-eth-02',
                    'Explainability concerns whether decisions can be:',
                    ['Understood by humans', 'Stored on disk', 'Sorted quickly', 'Printed'],
                    'Understood by humans'),
                   ('ai-eth-03',
                    'Privacy in AI concerns:',
                    ['Responsible handling of personal data',
                     'Only model size',
                     'Only code formatting',
                     'Only CPU usage'],
                    'Responsible handling of personal data'),
                   ('ai-eth-04',
                    'Fairness aims to reduce:',
                    ['Unjustified disparities', 'All model errors to zero', 'All data storage', 'All computation'],
                    'Unjustified disparities')]},
 'C++': {'Syntax & STL': [('cpp-syn-01',
                           'Which header provides std::vector?',
                           ['<vector>', '<arraylist>', '<listvector>', '<container>'],
                           '<vector>'),
                          ('cpp-syn-02', 'Which symbol ends a typical C++ statement?', [';', ';', '.', ':'], ';'),
                          ('cpp-syn-03',
                           'Which keyword declares a constant variable?',
                           ['const', 'constant', 'fixed', 'readonly'],
                           'const'),
                          ('cpp-syn-04',
                           'Which standard namespace commonly contains STL types?',
                           ['std', 'cpp', 'stl', 'system'],
                           'std')],
         'OOP': [('cpp-oop-01',
                  'A class is a blueprint for:',
                  ['Objects', 'Loops', 'Files', 'Threads only'],
                  'Objects'),
                 ('cpp-oop-02',
                  'Which feature allows a derived class to reuse a base class?',
                  ['Inheritance', 'Compilation', 'Iteration', 'Indexing'],
                  'Inheritance'),
                 ('cpp-oop-03',
                  'A constructor is called when an object is:',
                  ['Created', 'Deleted only', 'Printed', 'Sorted'],
                  'Created'),
                 ('cpp-oop-04',
                  'Which concept allows the same interface to have different implementations?',
                  ['Polymorphism', 'Hashing', 'Caching', 'Parsing'],
                  'Polymorphism')],
         'Pointers': [('cpp-ptr-01',
                       'A pointer stores:',
                       ['An address', 'A class only', 'A file', 'A loop count only'],
                       'An address'),
                      ('cpp-ptr-02', 'Which operator obtains the address of a variable?', ['&', '*', '->', '::'], '&'),
                      ('cpp-ptr-03', 'Which operator dereferences a pointer?', ['*', '&', '->>', '%'], '*'),
                      ('cpp-ptr-04',
                       'A null pointer represents:',
                       ['No valid object address', 'An integer always', 'A file', 'A reference to all objects'],
                       'No valid object address')],
         'Templates': [('cpp-temp-01',
                        'Templates support:',
                        ['Generic programming', 'Only graphics', 'Only networking', 'Only SQL'],
                        'Generic programming'),
                       ('cpp-temp-02',
                        'Which keyword begins a template declaration?',
                        ['template', 'generic', 'typenameonly', 'classonly'],
                        'template'),
                       ('cpp-temp-03',
                        'A function template can work with:',
                        ['Multiple data types', 'Only int', 'Only string', 'Only pointers'],
                        'Multiple data types'),
                       ('cpp-temp-04',
                        'In a template, typename is commonly used to declare a:',
                        ['Type parameter', 'Loop', 'Object instance', 'File'],
                        'Type parameter')],
         'STL Algorithms': [('cpp-stl-01',
                             'Which STL algorithm sorts a range?',
                             ['std::sort', 'std::order', 'std::arrange', 'std::sequence'],
                             'std::sort'),
                            ('cpp-stl-02',
                             'Which container provides fast indexed access?',
                             ['vector', 'list', 'set only', 'map only'],
                             'vector'),
                            ('cpp-stl-03',
                             'Which container stores unique sorted keys?',
                             ['set', 'vector', 'queue', 'stack'],
                             'set'),
                            ('cpp-stl-04',
                             'Which container stores key-value pairs?',
                             ['map', 'vector', 'stack', 'queue'],
                             'map')]},
 'P&S': {'Probability': [('ps-prob-01', 'Probability of an impossible event is:', ['0', '1', '-1', '0.5'], '0'),
                         ('ps-prob-02', 'Probability of a certain event is:', ['0', '1', '-1', '0.5'], '1'),
                         ('ps-prob-03',
                          'For equally likely outcomes, probability is:',
                          ['Favorable outcomes / total outcomes',
                           'Total / favorable',
                           'Favorable + total',
                           'Difference'],
                          'Favorable outcomes / total outcomes'),
                         ('ps-prob-04',
                          'The probability of an event and its complement sums to:',
                          ['1', '0', '2', '0.5'],
                          '1')],
         'Random Variables': [('ps-rv-01',
                               'A random variable assigns a numerical value to:',
                               ['Outcomes of a random experiment',
                                'Only constants',
                                'Only equations',
                                'Only databases'],
                               'Outcomes of a random experiment'),
                              ('ps-rv-02',
                               'A discrete random variable has values that are:',
                               ['Countable', 'Only continuous', 'Only negative', 'Always infinite decimals'],
                               'Countable'),
                              ('ps-rv-03',
                               'A continuous random variable can take values in:',
                               ['An interval', 'Only integers', 'Only zero', 'Only categories'],
                               'An interval'),
                              ('ps-rv-04',
                               'The expected value represents the:',
                               ['Mean/long-run average', 'Maximum only', 'Minimum only', 'Variance only'],
                               'Mean/long-run average')],
         'Distributions': [('ps-dist-01',
                            'A Bernoulli distribution models:',
                            ['One trial with two outcomes',
                             'Only continuous data',
                             'Only three outcomes',
                             'A time series'],
                            'One trial with two outcomes'),
                           ('ps-dist-02',
                            'The binomial distribution models the number of successes in:',
                            ['Fixed independent Bernoulli trials',
                             'Any continuous interval',
                             'One deterministic trial',
                             'Only normal data'],
                            'Fixed independent Bernoulli trials'),
                           ('ps-dist-03',
                            'The normal distribution is:',
                            ['Continuous and bell-shaped', 'Discrete and rectangular', 'Always skewed', 'Only uniform'],
                            'Continuous and bell-shaped'),
                           ('ps-dist-04',
                            'The Poisson distribution is often used for:',
                            ['Counts of events in a fixed interval',
                             'Only heights',
                             'Only percentages',
                             'Only continuous temperatures'],
                            'Counts of events in a fixed interval')],
         'Statistics': [('ps-stat-01',
                         'The mean is calculated by:',
                         ['Sum of values / number of values',
                          'Largest - smallest',
                          'Middle value only',
                          'Product of values'],
                         'Sum of values / number of values'),
                        ('ps-stat-02',
                         'The median is the:',
                         ['Middle ordered value', 'Most frequent value', 'Average of extremes', 'Largest value'],
                         'Middle ordered value'),
                        ('ps-stat-03',
                         'The mode is the:',
                         ['Most frequent value', 'Middle value', 'Average', 'Range'],
                         'Most frequent value'),
                        ('ps-stat-04',
                         'Variance measures:',
                         ['Spread around the mean', 'Only central location', 'Only sample size', 'Only maximum'],
                         'Spread around the mean')],
         'Hypothesis Testing': [('ps-ht-01',
                                 'The null hypothesis is commonly denoted:',
                                 ['H0', 'H1 only', 'Ha only', 'Hx'],
                                 'H0'),
                                ('ps-ht-02',
                                 'A p-value is used to assess evidence against:',
                                 ['The null hypothesis',
                                  'The sample mean only',
                                  'The population size',
                                  'The confidence interval only'],
                                 'The null hypothesis'),
                                ('ps-ht-03',
                                 'A significance level is often denoted by:',
                                 ['α', 'β only', 'μ', 'σ only'],
                                 'α'),
                                ('ps-ht-04',
                                 'Rejecting H0 when it is true is a:',
                                 ['Type I error', 'Type II error', 'Sampling mean', 'Confidence level'],
                                 'Type I error')]},
 'ADSAA': {'Advanced Data Structures': [('adsaa-ads-01',
                                         'Which structure is commonly used for efficient range queries?',
                                         ['Segment tree', 'Stack', 'Queue', 'Plain array only'],
                                         'Segment tree'),
                                        ('adsaa-ads-02',
                                         'A trie is especially useful for:',
                                         ['Prefix/string queries',
                                          'Matrix multiplication',
                                          'CPU scheduling',
                                          'File compression only'],
                                         'Prefix/string queries'),
                                        ('adsaa-ads-03',
                                         'A heap supports efficient:',
                                         ['Priority access',
                                          'Random graph traversal',
                                          'SQL joins',
                                          'String matching only'],
                                         'Priority access'),
                                        ('adsaa-ads-04',
                                         'A disjoint-set structure supports:',
                                         ['Union and find operations',
                                          'Push and pop only',
                                          'SQL SELECT',
                                          'Tree traversal only'],
                                         'Union and find operations')],
           'Algorithms': [('adsaa-alg-01',
                           'Binary search requires the search data to be:',
                           ['Sorted', 'Encrypted', 'Hashed always', 'Random'],
                           'Sorted'),
                          ('adsaa-alg-02',
                           'Merge sort has worst-case time complexity:',
                           ['O(n log n)', 'O(n)', 'O(log n)', 'O(n²)'],
                           'O(n log n)'),
                          ('adsaa-alg-03',
                           "Dijkstra's algorithm finds shortest paths with:",
                           ['Non-negative edge weights', 'Only negative weights', 'No weights', 'Only trees'],
                           'Non-negative edge weights'),
                          ('adsaa-alg-04',
                           'Topological sorting applies to:',
                           ['Directed acyclic graphs', 'Undirected complete graphs only', 'Heaps', 'Arrays only'],
                           'Directed acyclic graphs')],
           'Complexity': [('adsaa-com-01',
                           'O(1) means:',
                           ['Constant time', 'Linear time', 'Logarithmic time', 'Quadratic time'],
                           'Constant time'),
                          ('adsaa-com-02',
                           'Which grows fastest asymptotically?',
                           ['O(n²)', 'O(n log n)', 'O(n)', 'O(log n)'],
                           'O(n²)'),
                          ('adsaa-com-03',
                           'Space complexity measures:',
                           ['Additional memory usage as input grows',
                            'CPU frequency',
                            'Network bandwidth only',
                            'Number of files'],
                           'Additional memory usage as input grows'),
                          ('adsaa-com-04',
                           'An algorithm with O(log n) usually reduces the problem by a:',
                           ['Constant factor or multiplicative ratio',
                            'One element only always',
                            'Random amount',
                            'Fixed output'],
                           'Constant factor or multiplicative ratio')],
           'Dynamic Programming': [('adsaa-dp-01',
                                    'Dynamic programming is useful when subproblems:',
                                    ['Overlap and optimal substructure exists',
                                     'Are always unrelated',
                                     'Have no solutions',
                                     'Are only strings'],
                                    'Overlap and optimal substructure exists'),
                                   ('adsaa-dp-02',
                                    'Memoization stores results of:',
                                    ['Previously solved subproblems',
                                     'All input files',
                                     'Only final answers',
                                     'Only graph edges'],
                                    'Previously solved subproblems'),
                                   ('adsaa-dp-03',
                                    'Tabulation usually builds a solution:',
                                    ['Bottom-up', 'Only randomly', 'Only top-down', 'Without subproblems'],
                                    'Bottom-up'),
                                   ('adsaa-dp-04',
                                    'The Fibonacci sequence is a common example for:',
                                    ['Dynamic programming', 'SQL normalization', 'Cache mapping only', 'BFS only'],
                                    'Dynamic programming')],
           'Greedy Algorithms': [('adsaa-gr-01',
                                  'A greedy algorithm chooses:',
                                  ['The locally best option at each step',
                                   'All options exhaustively',
                                   'Only random options',
                                   'Only the final option'],
                                  'The locally best option at each step'),
                                 ('adsaa-gr-02',
                                  "Kruskal's algorithm builds a:",
                                  ['Minimum spanning tree',
                                   'Shortest path tree from one source',
                                   'Binary search tree',
                                   'Trie'],
                                  'Minimum spanning tree'),
                                 ('adsaa-gr-03',
                                  "Prim's algorithm also finds a:",
                                  ['Minimum spanning tree', 'Maximum flow always', 'Topological order', 'Hash table'],
                                  'Minimum spanning tree'),
                                 ('adsaa-gr-04',
                                  'Greedy algorithms are correct when the problem has suitable:',
                                  ['Greedy-choice property and optimal substructure',
                                   'Only recursion',
                                   'Only arrays',
                                   'Only sorting'],
                                  'Greedy-choice property and optimal substructure')]}}

PUZZLES = [
    {"id":"pz-01","title":"Logic","question":"I am an odd number. Remove one letter and I become even. What number am I?","answer":"seven"},
    {"id":"pz-02","title":"Sequence","question":"What comes next: 2, 4, 8, 16, ?","answer":"32"},
    {"id":"pz-03","title":"Riddle","question":"The more you take, the more you leave behind. What are they?","answer":"footsteps"},
    {"id":"pz-04","title":"Sequence","question":"What comes next: 3, 6, 12, 24, ?","answer":"48"},
    {"id":"pz-05","title":"Logic","question":"If all roses are flowers and some flowers fade, can we conclude all roses fade?","answer":"no"},
    {"id":"pz-06","title":"Number","question":"What is the smallest prime number?","answer":"2"},
    {"id":"pz-07","title":"Riddle","question":"What has keys but cannot open locks?","answer":"keyboard"},
    {"id":"pz-08","title":"Logic","question":"A clock shows 3:00. What is the angle between the hands?","answer":"90"},
    {"id":"pz-09","title":"Sequence","question":"What comes next: 1, 1, 2, 3, 5, ?","answer":"8"},
    {"id":"pz-10","title":"Riddle","question":"What gets wetter the more it dries?","answer":"towel"},
    {"id":"pz-11","title":"Logic","question":"How many sides does a hexagon have?","answer":"6"},
    {"id":"pz-12","title":"Number","question":"What is 15% of 200?","answer":"30"},
    {"id":"pz-13","title":"Riddle","question":"What has a face and two hands but no arms or legs?","answer":"clock"},
    {"id":"pz-14","title":"Sequence","question":"What comes next: 5, 10, 20, 40, ?","answer":"80"},
    {"id":"pz-15","title":"Logic","question":"If today is Monday, what day is 10 days later?","answer":"thursday"},
    {"id":"pz-16","title":"Riddle","question":"What can travel around the world while staying in one corner?","answer":"stamp"},
    {"id":"pz-17","title":"Number","question":"What is the square of 12?","answer":"144"},
    {"id":"pz-18","title":"Logic","question":"How many months have 28 days?","answer":"12"},
    {"id":"pz-19","title":"Riddle","question":"What has one eye but cannot see?","answer":"needle"},
    {"id":"pz-20","title":"Sequence","question":"What comes next: 10, 20, 30, 40, ?","answer":"50"},
]

DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2}

# Demo credentials. For deployment, set DEMO_USERNAME / DEMO_PASSWORD
# in Streamlit secrets. The fallback is only for local demonstration.
try:
    DEMO_USERNAME = st.secrets.get("DEMO_USERNAME", "demo")
    DEMO_PASSWORD = st.secrets.get("DEMO_PASSWORD", "password")
except Exception:
    DEMO_USERNAME = "demo"
    DEMO_PASSWORD = "password"

# ============================================================
# DATABASE
# ============================================================
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS preferences (
        user_id INTEGER PRIMARY KEY,
        subjects_json TEXT NOT NULL,
        exam_date TEXT,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        topic TEXT NOT NULL,
        minutes INTEGER NOT NULL,
        completed INTEGER NOT NULL,
        started_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS quiz_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        topic TEXT NOT NULL,
        question_id TEXT NOT NULL,
        correct INTEGER NOT NULL,
        score_percent REAL NOT NULL,
        difficulty TEXT NOT NULL,
        study_minutes INTEGER NOT NULL,
        attempted_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS coding_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        language TEXT NOT NULL,
        attempted INTEGER NOT NULL,
        solved INTEGER NOT NULL,
        minutes INTEGER NOT NULL,
        difficulty TEXT NOT NULL,
        logged_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS stress_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        level INTEGER NOT NULL,
        note TEXT,
        logged_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS puzzle_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        puzzle_id TEXT NOT NULL,
        solved INTEGER NOT NULL,
        attempted_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS subject_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        day TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        subject TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def authenticate(username, password):
    if username == DEMO_USERNAME and password == DEMO_PASSWORD:
        conn = get_conn()
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row:
            user_id = row[0]
        else:
            cur = conn.execute(
                "INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)",
                (username, hash_password(password), now().isoformat(timespec="seconds")),
            )
            user_id = cur.lastrowid
            conn.execute(
                "INSERT INTO preferences(user_id,subjects_json,exam_date,updated_at) VALUES(?,?,?,?)",
                (user_id, json.dumps(ALL_SUBJECTS), str(dt.date.today() + dt.timedelta(days=30)), now().isoformat()),
            )
            conn.commit()
        conn.close()
        return user_id

    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM users WHERE username=? AND password_hash=?",
        (username.strip(), hash_password(password)),
    ).fetchone()
    conn.close()
    return row[0] if row else None


def now():
    return dt.datetime.now()


def load_preferences(user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT subjects_json, exam_date FROM preferences WHERE user_id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        return ALL_SUBJECTS[:], str(dt.date.today() + dt.timedelta(days=30))
    try:
        subjects = json.loads(row[0])
    except Exception:
        subjects = ALL_SUBJECTS[:]
    return subjects or ALL_SUBJECTS[:], row[1]


def save_preferences(user_id, subjects, exam_date):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO preferences(user_id,subjects_json,exam_date,updated_at)
        VALUES(?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
            subjects_json=excluded.subjects_json,
            exam_date=excluded.exam_date,
            updated_at=excluded.updated_at
        """,
        (user_id, json.dumps(subjects), exam_date, now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def save_study(user_id, subject, topic, minutes, completed):
    conn = get_conn()
    conn.execute(
        """INSERT INTO study_sessions
        (user_id,subject,topic,minutes,completed,started_at)
        VALUES(?,?,?,?,?,?)""",
        (user_id, subject, topic, int(minutes), int(completed), now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def save_quiz_rows(user_id, rows):
    conn = get_conn()
    conn.executemany(
        """INSERT INTO quiz_attempts
        (user_id,subject,topic,question_id,correct,score_percent,
         difficulty,study_minutes,attempted_at)
        VALUES(?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    conn.close()


def save_coding(user_id, language, attempted, solved, minutes, difficulty):
    conn = get_conn()
    conn.execute(
        """INSERT INTO coding_logs
        (user_id,language,attempted,solved,minutes,difficulty,logged_at)
        VALUES(?,?,?,?,?,?,?)""",
        (user_id, language, int(attempted), int(solved), int(minutes), difficulty,
         now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def save_stress(user_id, level, note):
    conn = get_conn()
    conn.execute(
        "INSERT INTO stress_logs(user_id,level,note,logged_at) VALUES(?,?,?,?)",
        (user_id, int(level), note, now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def save_puzzle(user_id, puzzle_id, solved):
    conn = get_conn()
    conn.execute(
        "INSERT INTO puzzle_attempts(user_id,puzzle_id,solved,attempted_at) VALUES(?,?,?,?)",
        (user_id, puzzle_id, int(solved), now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def save_slot(user_id, day, time_slot, subject):
    conn = get_conn()
    conn.execute(
        "INSERT INTO subject_slots(user_id,day,time_slot,subject) VALUES(?,?,?,?)",
        (user_id, day, time_slot, subject),
    )
    conn.commit()
    conn.close()


def slots_df():
    return query_df(
        st.session_state.user_id,
        "subject_slots",
        "day,time_slot,subject",
    )


def query_df(user_id, table, columns):
    conn = get_conn()
    df = pd.read_sql_query(
        f"SELECT {columns} FROM {table} WHERE user_id=? ORDER BY rowid DESC".format(
            columns=columns, table=table
        ),
        conn,
        params=(user_id,),
    )
    conn.close()
    return df


def quiz_df():
    return query_df(
        st.session_state.user_id,
        "quiz_attempts",
        "subject,topic,question_id,correct,score_percent,difficulty,study_minutes,attempted_at",
    )


def study_df():
    return query_df(
        st.session_state.user_id,
        "study_sessions",
        "subject,topic,minutes,completed,started_at",
    )


def coding_df():
    return query_df(
        st.session_state.user_id,
        "coding_logs",
        "language,attempted,solved,minutes,difficulty,logged_at",
    )


def stress_df():
    return query_df(
        st.session_state.user_id,
        "stress_logs",
        "level,note,logged_at",
    )


def puzzle_df():
    return query_df(
        st.session_state.user_id,
        "puzzle_attempts",
        "puzzle_id,solved,attempted_at",
    )


def used_question_ids(subject, topic):
    df = quiz_df()
    if df.empty:
        return set()
    return set(
        df[(df["subject"] == subject) & (df["topic"] == topic)]["question_id"].astype(str)
    )


def used_puzzle_ids():
    df = puzzle_df()
    if df.empty:
        return set()
    return set(df["puzzle_id"].astype(str))


# ============================================================
# QUESTION BANK PREPARATION
# ============================================================
def prepared_bank():
    result = {}
    for subject, topics in QUESTION_BANK.items():
        result[subject] = {}
        for topic, items in topics.items():
            result[subject][topic] = []
            n = len(items)
            for i, item in enumerate(items):
                difficulty = "Easy" if i == 0 else ("Hard" if i == n - 1 else "Medium")
                result[subject][topic].append({
                    "id": item[0],
                    "q": item[1],
                    "options": item[2],
                    "answer": item[3],
                    "difficulty": difficulty,
                })
    return result


BANK = prepared_bank()


def topic_average(subject, topic):
    df = quiz_df()
    if df.empty:
        return None
    x = df[(df["subject"] == subject) & (df["topic"] == topic)]
    if x.empty:
        return None
    return float(x["score_percent"].mean())


def recommended_difficulty(subject, topic):
    avg = topic_average(subject, topic)
    if avg is None:
        return "Medium"
    if avg < 50:
        return "Easy"
    if avg < 80:
        return "Medium"
    return "Hard"


def question_count(minutes):
    if minutes <= 15:
        return 2
    if minutes <= 25:
        return 3
    return 4


def select_unique_questions(subject, topic, minutes):
    pool = BANK.get(subject, {}).get(topic, [])
    used = used_question_ids(subject, topic)
    unused = [q for q in pool if q["id"] not in used]

    if not unused:
        return []

    target = min(question_count(minutes), len(unused))
    desired = recommended_difficulty(subject, topic)

    preferred = [q for q in unused if q["difficulty"] == desired]
    other = [q for q in unused if q["difficulty"] != desired]
    random.shuffle(preferred)
    random.shuffle(other)
    ordered = preferred + other
    return ordered[:target]


def weak_topic():
    df = quiz_df()
    if df.empty:
        return None
    grouped = (
        df.groupby(["subject", "topic"], as_index=False)["score_percent"]
        .mean()
        .sort_values("score_percent")
    )
    row = grouped.iloc[0]
    return row["subject"], row["topic"], float(row["score_percent"])


# ============================================================
# SESSION STATE
# ============================================================
defaults = {
    "logged_in": False,
    "user_id": None,
    "username": "",
    "page": "Dashboard",
    "subjects": ALL_SUBJECTS[:],
    "exam_date": str(dt.date.today() + dt.timedelta(days=30)),
    "timer_running": False,
    "timer_end": None,
    "timer_duration": 25,
    "timer_subject": ALL_SUBJECTS[0],
    "timer_topic": TOPICS[ALL_SUBJECTS[0]][0],
    "timer_completed": False,
    "quiz_unlocked": None,
    "quiz_questions": [],
    "quiz_answers": {},
    "quiz_token": "",
    "quiz_result": None,
    "coding_streak": 0,
    "study_streak": 0,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def load_user():
    subjects, exam = load_preferences(st.session_state.user_id)
    st.session_state.subjects = [s for s in subjects if s in ALL_SUBJECTS] or ALL_SUBJECTS[:]
    st.session_state.exam_date = exam


def go(page):
    st.session_state.page = page


def study_streak_days():
    df = study_df()
    if df.empty:
        return 0
    dates = set(pd.to_datetime(df["started_at"]).dt.date.tolist())
    dates = {d for d in dates if d is not None}
    if not dates:
        return 0
    streak = 0
    day = max(dates)
    while day in dates:
        streak += 1
        day -= dt.timedelta(days=1)
    return streak


def coding_streak_days():
    df = coding_df()
    if df.empty:
        return 0
    dates = set(pd.to_datetime(df["logged_at"]).dt.date.tolist())
    if not dates:
        return 0
    streak = 0
    day = max(dates)
    while day in dates:
        streak += 1
        day -= dt.timedelta(days=1)
    return streak


def overall_progress():
    s = study_df()
    q = quiz_df()
    study_score = min(100, int((s["minutes"].sum() / 240) * 100)) if not s.empty else 0
    quiz_score = int(q["score_percent"].mean()) if not q.empty else 0
    return int(study_score * 0.55 + quiz_score * 0.45)


def smart_recommendation():
    weak = weak_topic()
    if weak and weak[2] < 70:
        return f"Focus next on **{weak[1]}** ({weak[0]}). Your current average is **{weak[2]:.0f}%**."
    pending_subjects = st.session_state.subjects
    if pending_subjects:
        return f"Choose a topic from **{pending_subjects[0]}**, study with the timer, then take its fresh topic quiz."
    return "Start a study session to build your personalized recommendation."


# ============================================================
# INITIALIZE
# ============================================================
init_db()

# ============================================================
# LOGIN
# ============================================================
if not st.session_state.logged_in:
    st.markdown(
        "<div style='text-align:center;padding:45px 10px 10px'>"
        "<div style='font-size:72px'>🧠</div>"
        "<h1 style='color:#4A90E2;font-size:46px'>MindMate</h1>"
        "<p style='font-size:19px;color:#666'>Smart Study Companion</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("🔐 Login", use_container_width=True)
        if submit:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                user_id = authenticate(username, password)
                if user_id:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username.strip()
                    load_user()
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        st.info(f"Demo: **{DEMO_USERNAME}** / **{DEMO_PASSWORD}**")
    st.stop()

# ============================================================
# SIDEBAR / FINAL MODULE ORDER
# ============================================================
with st.sidebar:
    st.markdown("## 🧠 MindMate")
    st.caption(f"Welcome, **{st.session_state.username}**")
    st.divider()

    pages = [
        "🏠 Dashboard",
        "📚 Study Planner",
        "📅 Tomorrow's Plan",
        "📝 Adaptive Quiz",
        "💬 Doubt Chatbot",
        "💻 Coding Tracker",
        "😌 Stress Monitor",
        "🧩 Puzzle Zone",
        "📊 Analytics",
        "⚙️ Settings",
    ]

    labels = [p.split(" ", 1)[1] for p in pages]
    current = st.session_state.page if st.session_state.page in labels else "Dashboard"
    selected_index = labels.index(current)

    selected = st.radio(
        "Navigation",
        labels,
        index=selected_index,
        key="navigation",
    )
    if selected != st.session_state.page:
        st.session_state.page = selected
        st.rerun()

    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ============================================================
# TIMER CHECK
# ============================================================
if st.session_state.timer_running:
    remaining = max(0, int(st.session_state.timer_end - time.time()))
    if remaining <= 0:
        st.session_state.timer_running = False
        st.session_state.timer_completed = True
        st.session_state.quiz_unlocked = {
            "subject": st.session_state.timer_subject,
            "topic": st.session_state.timer_topic,
            "minutes": st.session_state.timer_duration,
        }
        save_study(
            st.session_state.user_id,
            st.session_state.timer_subject,
            st.session_state.timer_topic,
            st.session_state.timer_duration,
            1,
        )
        st.success("🎉 Study session completed. Your topic quiz is unlocked!")
    else:
        st.session_state.timer_remaining = remaining

# ============================================================
# DASHBOARD
# ============================================================
if st.session_state.page == "Dashboard":
    st.title("🏠 Dashboard")
    st.caption("Your semester study command center.")

    exam = dt.date.fromisoformat(st.session_state.exam_date)
    days_left = max(0, (exam - dt.date.today()).days)

    qdf = quiz_df()
    sdf = study_df()
    cdf = coding_df()
    stress = stress_df()

    quiz_avg = float(qdf["score_percent"].mean()) if not qdf.empty else 0
    today_minutes = (
        int(sdf[pd.to_datetime(sdf["started_at"]).dt.date == dt.date.today()]["minutes"].sum())
        if not sdf.empty else 0
    )
    stress_level = int(stress.iloc[0]["level"]) if not stress.empty else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("⏳ Exam", f"{days_left} days")
    c2.metric("📚 Today", f"{today_minutes} min")
    c3.metric("📝 Quiz Avg", f"{quiz_avg:.0f}%")
    c4.metric("💻 Coding Streak", f"{coding_streak_days()} days")
    c5.metric("📈 Progress", f"{overall_progress()}%")

    st.subheader("🎯 Smart Recommendation")
    st.info(smart_recommendation())

    st.subheader("📚 Your Semester Subjects")
    cols = st.columns(min(4, max(1, len(st.session_state.subjects))))
    for i, subject in enumerate(st.session_state.subjects):
        cols[i % len(cols)].success(subject)

    st.subheader("🗓️ Subject Slotting")
    slots = slots_df()
    if slots.empty:
        st.caption("Add your weekly subject slots from Settings.")
    else:
        st.dataframe(slots.head(12), use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⏰ Next Exam")
        st.write(f"**{exam.strftime('%d %B %Y')}**")
        st.progress(max(0, min(1, 1 - days_left / 365)))

        st.subheader("📋 Today's Focus")
        if st.session_state.quiz_unlocked:
            u = st.session_state.quiz_unlocked
            st.success(f"Quiz ready: **{u['subject']} → {u['topic']}**")
            if st.button("📝 Take Unlocked Quiz", use_container_width=True):
                go("Adaptive Quiz")
                st.rerun()
        else:
            st.write("Start a topic study timer from Study Planner.")

    with col2:
        st.subheader("📅 Tomorrow Preview")
        weak = weak_topic()
        if weak:
            st.write(f"1. 45 min — Revise **{weak[1]}** ({weak[0]})")
            st.write(f"2. 30 min — Fresh **{weak[1]}** quiz")
        else:
            st.write("1. 30 min — Study your highest-priority topic")
            st.write("2. 15–25 min — Complete a topic quiz")
        st.write("3. 30 min — Coding practice")
        st.write("4. 10 min — Stress check and break")

    st.subheader("📊 Weekly Study Activity")
    if not sdf.empty:
        tmp = sdf.copy()
        tmp["date"] = pd.to_datetime(tmp["started_at"]).dt.date.astype(str)
        daily = tmp.groupby("date")["minutes"].sum().tail(7)
        st.bar_chart(daily)
    else:
        st.info("Complete study sessions to see your real activity here.")

# ============================================================
# STUDY PLANNER
# ============================================================
elif st.session_state.page == "Study Planner":
    st.title("📚 Study Planner")
    st.caption("Select a semester subject and topic. Finish the timer to unlock the quiz.")

    subject = st.selectbox("Subject", st.session_state.subjects)
    topic = st.selectbox("Topic", TOPICS[subject])
    duration = st.selectbox("Study duration", [15, 25, 30, 45, 60])

    st.markdown(f"### 📖 {subject} → {topic}")

    if st.session_state.timer_running:
        remaining = max(0, int(st.session_state.timer_end - time.time()))
        mins, secs = divmod(remaining, 60)
        elapsed = st.session_state.timer_duration * 60 - remaining
        st.metric("⏱️ Time Remaining", f"{mins:02d}:{secs:02d}")
        st.progress(max(0, min(1, elapsed / max(1, st.session_state.timer_duration * 60))))
        st.warning("Stay on this topic until the timer finishes.")
        time.sleep(1)
        st.rerun()

    elif st.session_state.timer_completed and st.session_state.quiz_unlocked:
        u = st.session_state.quiz_unlocked
        st.success(f"🎉 Completed {u['minutes']} minutes of **{u['topic']}**.")
        st.info("Your unique topic quiz is unlocked.")
        if st.button("📝 Take Topic Quiz", use_container_width=True):
            go("Adaptive Quiz")
            st.rerun()
        if st.button("🔄 Start Another Session"):
            st.session_state.timer_completed = False
            st.session_state.quiz_unlocked = None
            st.rerun()

    else:
        st.info("The quiz unlocks only after the selected study timer is completed.")
        if st.button("▶️ Start Study Timer", use_container_width=True):
            st.session_state.timer_subject = subject
            st.session_state.timer_topic = topic
            st.session_state.timer_duration = duration
            st.session_state.timer_end = time.time() + duration * 60
            st.session_state.timer_running = True
            st.session_state.timer_completed = False
            st.session_state.quiz_unlocked = None
            st.rerun()

    st.divider()
    st.subheader("📚 Study History")
    sdf = study_df()
    if sdf.empty:
        st.info("No study sessions recorded yet.")
    else:
        st.dataframe(sdf.head(20), use_container_width=True, hide_index=True)

# ============================================================
# TOMORROW'S PLAN
# ============================================================
elif st.session_state.page == "Tomorrow's Plan":
    st.title("📅 Tomorrow's Plan")
    st.caption("Generated from your quiz performance, weak topics, study activity and semester subjects.")

    weak = weak_topic()
    if weak:
        st.success(f"🎯 Weak topic detected: **{weak[1]}** — {weak[2]:.0f}% average.")
    else:
        st.info("Complete at least one topic quiz to make the plan performance-aware.")

    if st.button("✨ Generate Smart Plan", use_container_width=True):
        plan = []
        if weak and weak[2] < 70:
            plan.append(f"45 min — Revise {weak[0]} → {weak[1]}")
            plan.append(f"30 min — Study timer + fresh quiz: {weak[1]}")
        else:
            subject = st.session_state.subjects[0]
            topic = TOPICS[subject][0]
            plan.append(f"30 min — Study {subject} → {topic}")
            plan.append(f"15–25 min — Topic quiz: {topic}")

        plan.append("30 min — Coding practice")
        plan.append("15 min — Revision of an unfinished topic")
        plan.append("10 min — Stress check + break")

        st.session_state.tomorrow_plan = plan

    if "tomorrow_plan" in st.session_state:
        for i, item in enumerate(st.session_state.tomorrow_plan, 1):
            st.success(f"{i}. {item}")

# ============================================================
# ADAPTIVE QUIZ
# ============================================================
elif st.session_state.page == "Adaptive Quiz":
    st.title("📝 Adaptive Topic Quiz")
    st.caption("Questions are topic-specific and previously used question IDs are never reused until the topic pool is exhausted.")

    unlocked = st.session_state.quiz_unlocked
    if unlocked:
        subject = unlocked["subject"]
        topic = unlocked["topic"]
        minutes = unlocked["minutes"]
        st.success(f"🔓 Unlocked: **{subject} → {topic}** after {minutes} minutes of study.")
    else:
        subject = st.selectbox("Subject", st.session_state.subjects)
        topic = st.selectbox("Topic", TOPICS[subject])
        minutes = st.selectbox("Study duration", [15,25,30,45,60])
        st.warning("Complete the Study Planner timer for this topic before starting its quiz.")

    avg = topic_average(subject, topic)
    difficulty = recommended_difficulty(subject, topic)
    pool = BANK.get(subject, {}).get(topic, [])
    used = used_question_ids(subject, topic)
    remaining = len(pool) - len(used)

    a,b,c = st.columns(3)
    a.metric("Recommended Difficulty", difficulty)
    b.metric("Question Pool", len(pool))
    c.metric("Unused Questions", max(0, remaining))

    if unlocked and not st.session_state.quiz_questions:
        selected_qs = select_unique_questions(subject, topic, minutes)
        if selected_qs:
            st.session_state.quiz_questions = selected_qs
            st.session_state.quiz_answers = {}
            st.session_state.quiz_token = now().isoformat()
        else:
            st.error("This topic's question pool has been completed. Add more questions to create another non-repeating quiz.")

    if st.session_state.quiz_questions:
        questions = st.session_state.quiz_questions
        st.write(f"**{len(questions)} unique questions** selected for this attempt.")

        for i, q in enumerate(questions):
            st.markdown(f"### Q{i+1}. {q['q']}")
            answer = st.radio(
                "Choose one:",
                q["options"],
                key=f"{st.session_state.quiz_token}_{q['id']}",
            )
            st.session_state.quiz_answers[q["id"]] = answer

        if st.button("✅ Submit Quiz", use_container_width=True):
            correct_count = sum(
                st.session_state.quiz_answers.get(q["id"]) == q["answer"]
                for q in questions
            )
            score = round(correct_count / len(questions) * 100)

            rows = []
            timestamp = now().isoformat(timespec="seconds")
            for q in questions:
                rows.append((
                    st.session_state.user_id,
                    subject,
                    topic,
                    q["id"],
                    int(st.session_state.quiz_answers.get(q["id"]) == q["answer"]),
                    score,
                    q["difficulty"],
                    minutes,
                    timestamp,
                ))
            save_quiz_rows(st.session_state.user_id, rows)

            st.session_state.quiz_result = {
                "score": score,
                "correct": correct_count,
                "total": len(questions),
                "subject": subject,
                "topic": topic,
            }
            st.session_state.quiz_questions = []
            st.session_state.quiz_answers = {}
            st.session_state.quiz_unlocked = None
            st.session_state.timer_completed = False
            st.rerun()

    if st.session_state.quiz_result:
        r = st.session_state.quiz_result
        st.divider()
        st.subheader("📊 Latest Result")
        x,y,z = st.columns(3)
        x.metric("Score", f"{r['score']}%")
        y.metric("Correct", f"{r['correct']}/{r['total']}")
        z.metric("Topic", r["topic"])

        if r["score"] >= 80:
            st.success("🟢 Strong — next time MindMate will prefer harder questions.")
        elif r["score"] >= 50:
            st.warning("🟡 OK — revise this topic and practise again.")
        else:
            st.error("🔴 Weak — this topic will be prioritized in recommendations.")

# ============================================================
# DOUBT CHATBOT
# ============================================================
elif st.session_state.page == "Doubt Chatbot":
    st.title("💬 Doubt Chatbot")
    st.caption("Rule-based academic helper. It can be replaced with an AI API later without changing the module structure.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role":"assistant","content":"Hi! Tell me your subject and doubt. I can give a concept explanation, example, revision hint, or practice question."}
        ]

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input("Ask your doubt...")
    if prompt:
        st.session_state.chat_history.append({"role":"user","content":prompt})
        text = prompt.lower()

        if "dbms" in text or "sql" in text:
            response = "For DBMS, first identify the tables, keys, relationships and required output. For SQL, break the problem into SELECT, FROM, JOIN, WHERE, GROUP BY and HAVING as needed."
        elif "ai" in text or "machine learning" in text:
            response = "For AI/ML doubts, identify the task first: classification, regression, clustering, search, or reasoning. Then choose the appropriate representation and algorithm."
        elif "c++" in text or "pointer" in text:
            response = "For C++, check types, object lifetime and pointer/reference ownership. If you share the code, I can explain it step by step."
        elif "python" in text:
            response = "For Python, send the exact error or code. I can explain the concept and suggest a corrected approach."
        elif "data structure" in text or "tree" in text or "graph" in text:
            response = "For Data Structures, identify the operation and its complexity first. Then choose the structure that gives the required access/update behavior."
        elif "physics" in text:
            response = "For Modern Physics, write the given quantities, the governing equation, substitute units consistently, and check the final dimension."
        elif "probability" in text or "statistics" in text:
            response = "For P&S, define the random experiment and event first, then select the probability/statistical formula that matches the data."
        else:
            response = "Tell me the subject, topic and exact question. I will break it into concept → given information → method → answer."

        st.session_state.chat_history.append({"role":"assistant","content":response})
        st.rerun()

# ============================================================
# CODING TRACKER
# ============================================================
elif st.session_state.page == "Coding Tracker":
    st.title("💻 Coding Tracker")
    st.caption("Track each language separately and automatically classify it as Strong, OK or Weak.")

    languages = ["C++", "Python", "C", "Java", "JavaScript", "SQL"]
    with st.form("coding_form"):
        a,b,c,d = st.columns(4)
        language = a.selectbox("Language", languages)
        attempted = b.number_input("Problems attempted", 1, 500, 5)
        solved = c.number_input("Problems solved", 0, 500, 4)
        minutes = d.number_input("Practice minutes", 0, 1000, 30)
        difficulty = st.selectbox("Main difficulty", ["Easy","Medium","Hard"])
        save = st.form_submit_button("➕ Save Coding Session", use_container_width=True)

    if save:
        solved = min(int(solved), int(attempted))
        save_coding(st.session_state.user_id, language, int(attempted), solved, int(minutes), difficulty)
        st.success("Coding session saved.")
        st.rerun()

    df = coding_df()
    if df.empty:
        st.info("Add coding sessions to see language strength.")
    else:
        grouped = df.groupby("language", as_index=False).agg(
            Attempted=("attempted","sum"),
            Solved=("solved","sum"),
            Minutes=("minutes","sum"),
        )
        grouped["Accuracy"] = (grouped["Solved"] / grouped["Attempted"] * 100).round(0)

        def language_status(x):
            if x >= 80:
                return "🟢 Strong"
            if x >= 50:
                return "🟡 OK"
            return "🔴 Weak"

        grouped["Status"] = grouped["Accuracy"].apply(language_status)

        st.subheader("📊 Language Performance")
        st.dataframe(grouped, use_container_width=True, hide_index=True)

        st.subheader("🎯 Your Coding Strength")
        for _, row in grouped.sort_values("Accuracy", ascending=False).iterrows():
            st.write(f"**{row['language']}** — {row['Accuracy']:.0f}% — {row['Status']}")
            st.progress(float(row["Accuracy"]) / 100)

        st.subheader("📈 Problems Solved by Language")
        st.bar_chart(grouped.set_index("language")["Solved"])

# ============================================================
# STRESS MONITOR
# ============================================================
elif st.session_state.page == "Stress Monitor":
    st.title("😌 Stress Monitor")
    st.caption("Wellbeing tracker for study planning; it is not a medical assessment.")

    current = int(stress_df().iloc[0]["level"]) if not stress_df().empty else 5
    level = st.slider("Current stress level", 1, 10, current)
    note = st.text_input("Optional note", placeholder="e.g. exam tomorrow, slept late")

    if st.button("💾 Save Stress Level", use_container_width=True):
        save_stress(st.session_state.user_id, level, note)
        st.success("Stress level recorded.")
        st.rerun()

    if level <= 3:
        st.success("😌 Low stress — good for focused study.")
    elif level <= 6:
        st.warning("🙂 Moderate stress — use shorter sessions and breaks.")
    else:
        st.error("😰 High stress — reduce workload and take a proper break.")

    df = stress_df()
    if not df.empty:
        chart = df.head(14).copy()
        chart["date"] = pd.to_datetime(chart["logged_at"]).dt.strftime("%d %b")
        st.line_chart(chart.set_index("date")["level"])

# ============================================================
# PUZZLE ZONE
# ============================================================
elif st.session_state.page == "Puzzle Zone":
    st.title("🧩 Puzzle Zone")
    st.caption("Puzzles are tracked by ID. A solved/attempted puzzle is not shown again.")

    used = used_puzzle_ids()
    available = [p for p in PUZZLES if p["id"] not in used]

    if not available:
        st.success("🎉 You have completed the entire puzzle bank. Add more puzzles for a new set.")
    else:
        if "active_puzzle_id" not in st.session_state or st.session_state.active_puzzle_id not in [p["id"] for p in available]:
            st.session_state.active_puzzle_id = random.choice(available)["id"]

        puzzle = next(p for p in available if p["id"] == st.session_state.active_puzzle_id)
        st.markdown(f"### {puzzle['title']}")
        st.write(puzzle["question"])

        answer = st.text_input("Your answer", key=f"puzzle_answer_{puzzle['id']}")
        a,b = st.columns(2)
        if a.button("✅ Check Answer", use_container_width=True):
            correct = answer.strip().lower() == puzzle["answer"].strip().lower()
            save_puzzle(st.session_state.user_id, puzzle["id"], int(correct))
            if correct:
                st.success("🎉 Correct! This puzzle is now permanently marked as used.")
            else:
                st.error(f"Not correct. Correct answer: **{puzzle['answer']}**")
            st.session_state.active_puzzle_id = None
            st.rerun()

        if b.button("➡️ Skip Puzzle", use_container_width=True):
            save_puzzle(st.session_state.user_id, puzzle["id"], 0)
            st.session_state.active_puzzle_id = None
            st.rerun()

    pdf = puzzle_df()
    solved = int(pdf["solved"].sum()) if not pdf.empty else 0
    st.metric("🧩 Puzzles completed/attempted", len(pdf))
    st.metric("🏆 Solved", solved)

# ============================================================
# ANALYTICS
# ============================================================
elif st.session_state.page == "Analytics":
    st.title("📊 Analytics")
    st.caption("Real activity from study sessions, quizzes, coding and stress logs.")

    sdf = study_df()
    qdf = quiz_df()
    cdf = coding_df()
    rdf = stress_df()

    study_minutes = int(sdf["minutes"].sum()) if not sdf.empty else 0
    quiz_avg = float(qdf["score_percent"].mean()) if not qdf.empty else 0
    coding_solved = int(cdf["solved"].sum()) if not cdf.empty else 0

    a,b,c,d = st.columns(4)
    a.metric("Study Minutes", study_minutes)
    b.metric("Quiz Average", f"{quiz_avg:.0f}%")
    c.metric("Coding Solved", coding_solved)
    d.metric("Study Streak", f"{study_streak_days()} days")

    st.subheader("🧠 Topic Strength")
    if qdf.empty:
        st.info("Complete quizzes to see topic strength.")
    else:
        topic_perf = (
            qdf.groupby(["subject","topic"], as_index=False)["score_percent"]
            .mean()
            .sort_values("score_percent")
        )
        topic_perf["Status"] = topic_perf["score_percent"].apply(
            lambda x: "🟢 Strong" if x >= 80 else ("🟡 OK" if x >= 50 else "🔴 Weak")
        )
        topic_perf["score_percent"] = topic_perf["score_percent"].round(0)
        st.dataframe(topic_perf, use_container_width=True, hide_index=True)
        st.bar_chart(topic_perf.set_index("topic")["score_percent"])

    st.subheader("💻 Language Strength")
    if cdf.empty:
        st.info("Log coding sessions to see language strength.")
    else:
        lang = cdf.groupby("language", as_index=False).agg(
            Attempted=("attempted","sum"),
            Solved=("solved","sum"),
            Minutes=("minutes","sum"),
        )
        lang["Accuracy"] = (lang["Solved"] / lang["Attempted"] * 100).round(0)
        lang["Status"] = lang["Accuracy"].apply(
            lambda x: "🟢 Strong" if x >= 80 else ("🟡 OK" if x >= 50 else "🔴 Weak")
        )
        st.dataframe(lang, use_container_width=True, hide_index=True)

    st.subheader("😌 Stress Trend")
    if rdf.empty:
        st.info("Record stress levels to see the trend.")
    else:
        chart = rdf.copy()
        chart["date"] = pd.to_datetime(chart["logged_at"]).dt.strftime("%d %b %H:%M")
        st.line_chart(chart.head(20).set_index("date")["level"])

# ============================================================
# SETTINGS
# ============================================================
elif st.session_state.page == "Settings":
    st.title("⚙️ Settings")
    st.caption("Configure your semester subjects, exam date and study preferences.")

    st.subheader("🎓 Semester Subjects")
    st.write("Select only the subjects you actually have this semester.")
    selected_subjects = st.multiselect(
        "My subjects",
        ALL_SUBJECTS,
        default=st.session_state.subjects,
    )

    st.subheader("📅 Exam")
    exam_date = st.date_input(
        "Next exam date",
        value=dt.date.fromisoformat(st.session_state.exam_date),
    )

    if st.button("💾 Save Semester Settings", use_container_width=True):
        if not selected_subjects:
            st.error("Select at least one subject.")
        else:
            st.session_state.subjects = selected_subjects
            st.session_state.exam_date = exam_date.isoformat()
            save_preferences(
                st.session_state.user_id,
                selected_subjects,
                exam_date.isoformat(),
            )
            st.success("Semester subjects and exam date saved.")

    st.divider()
    st.subheader("📚 Available Subject Bank")
    st.write(", ".join(ALL_SUBJECTS))
    st.caption("Each subject has topic-wise quiz questions. You can extend QUESTION_BANK later without changing the application flow.")

    st.divider()
    st.subheader("🗓️ Subject Slotting")
    st.caption("Create a simple weekly timetable for your semester subjects.")

    day = st.selectbox(
        "Day",
        ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
    )
    time_slot = st.selectbox(
        "Time",
        ["08:00","09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00","18:00","19:00"],
    )
    slot_subject = st.selectbox("Subject", st.session_state.subjects)

    if st.button("➕ Add Subject Slot", use_container_width=True):
        save_slot(st.session_state.user_id, day, time_slot, slot_subject)
        st.success(f"Added {slot_subject} on {day} at {time_slot}.")
        st.rerun()

    slots = slots_df()
    if not slots.empty:
        st.dataframe(slots, use_container_width=True, hide_index=True)

    st.subheader("🔐 Account")
    st.write(f"Logged in as **{st.session_state.username}**")

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption("MindMate • Study → Timer → Unique Quiz → Analyze → Improve")
