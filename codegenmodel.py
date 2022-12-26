#!/usr/bin/env python3
# Analyse et prépare les modèles
import colorama
from colorama import Fore, Back, Style

colorama.init(autoreset=True)
import os
import sys
from enum import Enum


class Dump(Enum):
    PHPMYADMIN = 1
    DBEAVER = 2
    WORKBENCH = 3
    UNKNOWN = 99


tables = []
keys = []

dump_status = Dump.UNKNOWN


def detect_signature(line):
    status = Dump.UNKNOWN
    if 'MySQL dump' in line:
        status = Dump.DBEAVER
    if 'phpMyAdmin SQL Dump' in line:
        status = Dump.PHPMYADMIN
    if 'Workbench' in line:
        status = Dump.WORKBENCH

    return status


def capitalize_all(s):
    if '_' in s:
        f = s.split('_')
        count = len(f)
        i = 0
        text: str = ""
        for p in f:
            if i < (count - 1):
                text += str(p.capitalize()) + '_'
            else:
                text += str(p.capitalize())
            i += 1
    else:
        text = s

    return text


def class_name_model(line):
    if '_' in line:
        s = capitalize_all(line)
        st = f'{s}Model'
    else:
        s = line.capitalize()
        st = f'{s}Model'
    return str(st)


def purify(keyword, string):
    s = string.replace(keyword, "").replace("`", "").replace("(", "").strip()
    return s


def purify2(keyword, string):
    s = string.replace(keyword, "") \
        .replace("`", "") \
        .replace("(", "") \
        .replace("IF NOT EXISTS", "").strip()
    s = s.split('.')
    if s:
        return s[1]

    return ''


def identify(line, keyword='CREATE TABLE', status=Dump.DBEAVER):
    s = ""
    if keyword in line:
        if status == Dump.DBEAVER:
            s = (purify(keyword, line))
        if status == Dump.WORKBENCH:
            s = purify2(keyword, line)
        return s


def detect_field(line):
    s = ""
    if 'NULL' in line:
        s = line.split("`")
    return s


def detect_primary_key(line):
    if 'PRIMARY KEY' in line:
        s = line.split("`")
        return s[1]
    return ''


def parse(lines):
    is_table = False
    is_primary_key = False
    fields = []
    table_primary_key = ""

    for line in lines:

        if 'CREATE TABLE' in line:
            is_table = True
            w_table = identify(line, 'CREATE TABLE')
            table = {"table": w_table}
            classname = class_name_model(str(w_table))

            table['classname'] = classname
            print('\n')
            print('_' * 40)
            print(f'📕Table {w_table}')
            print('_' * 40)

        if ')' and 'ENGINE' in line:
            is_table = False
            table['fields'] = fields
            tables.append(table)
            fields = []

        if is_table:
            field = detect_field(line)
            if len(field) > 0:
                fields.append(field[1])
                print(f'💬 {field[1]}')

        if is_primary_key:
            key = detect_primary_key(line)
            if key and table_primary_key:
                keys.append([table_primary_key, key])
            is_primary_key = False

        if 'ALTER TABLE' in line:
            is_table = False
            table_primary_key = identify(line, 'ALTER TABLE')
            print('_' * 40)
            print(f' \U0001f511 {table_primary_key}')

            is_primary_key = True


def parse_dbeaver(lines):
    is_table = False
    fields = []

    for line in lines:

        if 'CREATE TABLE' in line:
            is_table = True
            w_table = identify(line, 'CREATE TABLE')
            table = {"table": w_table}
            classname = class_name_model(str(w_table))
            table['classname'] = classname
            print('\n')
            print('_' * 40)
            print(f'📕Table {w_table}')
            print('_' * 40)

        if ')' and 'ENGINE' in line:
            is_table = False
            table['fields'] = fields
            tables.append(table)
            fields = []

        if is_table:
            field = detect_field(line)
            if len(field) > 0:
                fields.append(field[1])
                print(f'💬 {field[1]}')

            key = detect_primary_key(line)
            if key:
                print('_' * 40)
                keys.append([table['table'], key])
                print(f'\U0001f511 {key}')


def parse_workbench(lines):
    is_table = False
    fields = []
    table = {}

    for line in lines:

        if 'CREATE TABLE' in line:
            is_table = True
            w_table = identify(line, 'CREATE TABLE', dump_status)
            table = {"table": w_table}
            classname = class_name_model(str(w_table))
            table['classname'] = classname
            print('\n')
            print('_' * 40)
            print(f'📕Table {w_table}')
            print('_' * 40)
            fields = []

        if is_table:
            field = detect_field(line)
            if len(field) > 0:
                fields.append(field[1])
                print(f'💬 {field[1]}')

        if 'ENGINE =' in line:
            is_table = False
            table['fields'] = fields
            tables.append(table)

        if "PRIMARY KEY" in line:
            key = detect_primary_key(line)
            if key:
                print('_' * 40)
                keys.append([table['table'], key])
                print(f'\U0001f511 {key}')


def scan(file):
    with open(file, 'r') as f:
        lines = f.readlines()

    if 'phpMyAdmin' in lines[0]:
        if Dump.PHPMYADMIN == (detect_signature(lines[0])):
            print('DUMP phpMyAdmin')
            parse(lines)
    if 'dump' in lines[0]:
        if Dump.DBEAVER == (detect_signature(lines[0])):
            print('DUMP Dbeaver')
            parse_dbeaver(lines)
    if 'Workbench' in lines[0]:
        if Dump.WORKBENCH == (detect_signature(lines[0])):
            print('DUMP Workbench')
            parse_workbench(lines)


def create_file(table):
    template = os.getcwd() + "/template.model"
    with open(template) as f:
        buffer = f.readlines()

    fields = table['fields']
    st = ""
    index = 0
    for field in fields:
        field = str(field)
        if index == 0:
            st += f"'{field}',\n"
        else:
            st += f"\t\t'{field}',\n"
        index += 1

    text = ""
    primary_key = ""
    for key in keys:
        if key[0] == table['table']:
            primary_key = key[1]
            break

    for line in buffer:
        if '<CLASSNAME>' in line:
            line = line.replace("<CLASSNAME>", f"{table['classname']}")
        if '<TABLENAME>' in line:
            line = line.replace("<TABLENAME>", f"'{table['table']}'")
        if '<FIELDS>' in line:
            line = line.replace("<FIELDS>", st)
        if '<PRIMARYKEY>' in line:
            if primary_key:
                line = line.replace("<PRIMARYKEY>", f"protected $primaryKey = '{primary_key}';")
                line += '\tprotected $useAutoIncrement = true;\n'
            else:
                line = line.replace("<PRIMARYKEY>", "")

            line = line.replace("//", "")
        text += str(line)

    filename = os.getcwd() + f"/Models/{table['classname']}.php"
    with open(filename, "w+") as fw:
        fw.write(text)


def generateModels():
    for table in tables:
        create_file(table)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print(Fore.GREEN+'CodeGenModel Version 2.0')
    print(Fore.WHITE)

    opts = [opt for opt in sys.argv[1:] if opt.startswith("-")]
    args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    if args:
        scan(args[0])

    if "-h" in opts:
        print(Fore.LIGHTGREEN_EX)
        print(f"Usage: {sys.argv[0]} -c : suppression des fichiers modèles")
        print(f"Usage: {sys.argv[0]} --clear : suppression des fichiers modèles")
        print(f"Usage: {sys.argv[0]} -h : affiche l'aide des commandes et options")
        print(f"Usage: {sys.argv[0]} --help : affiche l'aide des commandes et options")
        print(f"Usage: {sys.argv[0]} -m : création du répertoire où se trouve les modèles")
        print(f"Usage: {sys.argv[0]} --model : création du répertoire où se trouve les modèles")
        print(f"Usage: {sys.argv[0]} -l : création du fichier log")
        print(f"Usage: {sys.argv[0]} --log : création du fichier log")
        print(f"Usage: {sys.argv[0]} -t : regénération du fichier template")
        print(f"Usage: {sys.argv[0]} --template : regénération du fichier template")
        exit(0)

    elif "-c" in opts:
        print('suppression des fichiers modèles')

    elif "--clear" in opts:
        print('suppression des fichiers modèles')

    elif "-m" in opts:
        print('création du répertoire modèle')

    elif "-model" in opts:
        print('création du répertoire modèle')

    elif "-l" in opts:
        print('création du fichier log')

    elif "--log" in opts:
        print('création du fichier log')

    elif "-t" in opts:
        print('regénération du template')

    elif "--template" in opts:
        print('regénération du template')

    elif "-g" in opts:
        generateModels()
        print("génération des fichier modèles")
    else:
        if not args:
            print ("Aucun dump trouvé")
            print ("Usage codegenmodel <dump file> [c|g|l|m]")
    print('_' * 40)
    exit(0)




# See PyCharm help at https://www.jetbrains.com/help/pycharm/
