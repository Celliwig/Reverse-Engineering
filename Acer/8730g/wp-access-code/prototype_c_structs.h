

struct mcu2_idata {
	char idata[0xe];
};

struct mcu2_itable {
	struct mcu2_idata table[0xe];
};
