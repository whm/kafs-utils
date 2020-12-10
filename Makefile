CFLAGS	:= $(shell python3-config --cflags)

RXGEN	:= ./rxgen/rxgen.pl $(wildcard ./rxgen/*.pm)

GENERATED := afs_xg.c afs_xg.h afs_py.c afs_py.h

pykafs.so: $(GENERATED)
	python3 setup.py build

#AFS_API	:= rpc-api/afsuuid.h rpc-api/vldb.xg
AFS_API	:= $(sort $(wildcard rpc-api/*.h)) $(sort $(wildcard rpc-api/*.xg))

.rxgen.check $(GENERATED): $(AFS_API) $(RXGEN)
	./rxgen/rxgen.pl $(AFS_API)
	touch .rxgen.check

clean:
	find \( -name "*~" -o -name "*.o" -o -name "*.so" \) -delete
	rm -rf build/
	rm -f $(GENERATED) .rxgen.check
