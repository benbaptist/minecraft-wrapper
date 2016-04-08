# -*- coding: utf-8 -*-

def args(arginput, i):
    try:
        return arginput[i]
    except:
        return ""

def argsAfter(arginput, i):
    try:
        return " ".join(arginput[i:])
    except:
        return ""
