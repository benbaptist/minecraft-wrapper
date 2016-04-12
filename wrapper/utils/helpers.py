# -*- coding: utf-8 -*-

def args(arginput, i):
    if not i >= len(arginput):
        return arginput[i]
    else:
        return ""

def argsAfter(arginput, i):
    return " ".join(arginput[i:])
