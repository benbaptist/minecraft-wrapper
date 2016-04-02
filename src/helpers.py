# -*- coding: utf-8 -*-

def args(input, i):
    try:
        return input[i]
    except:
        return ""

def argsAfter(input, i):
    try:
        return " ".join(input[i:])
    except:
        return ""