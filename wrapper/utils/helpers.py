# -*- coding: utf-8 -*-

def get_args(arginput, i):
    if not i >= len(arginput):
        return arginput[i]
    else:
        return ""

def get_argsAfter(arginput, i):
    return " ".join(arginput[i:])
