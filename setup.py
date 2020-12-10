from distutils.core import setup, Extension

# Example that has an rpcgen implementation that is run from setup.py
#
# http://git.linux-nfs.org/?p=iisaman/pynfs.git;a=tree;h=14b3085dcce30d941a7839241779639b80e6298b;hb=14b3085dcce30d941a7839241779639b80e6298b

setup(name = "kafs",
      version = "0.1",
      description = "AFS filesystem management scripting and commands",
      author = "David Howells",
      author_email = "dhowells@redhat.com",
      license = "GPLv2",
      ext_modules = [Extension("kafs",
                               sources = [ "afs_xg.c",
                                           "kafs.c",
                                           "afs_py.c",
                                           "py_passwd.c",
                                           "py_rxgen.c",
                                           "py_rxconn.c",
                                           "py_rxsplit.c",
                                           "af_rxrpc.c"
                                       ],
                             extra_compile_args = [
                                 "-O0",
                                 "-Wp,-U_FORTIFY_SOURCE",
                             ],
                             libraries = [
                                 "k5crypto",
                                 "krb5"
                             ]
                         )])
