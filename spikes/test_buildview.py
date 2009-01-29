from buildview import buildview

view = {'book': ['metadata.*.authors.*'],'post':['foo.*.bar.arg.*.koo','arg.*.foo']}

print buildview(view)
