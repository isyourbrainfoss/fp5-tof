// SPDX-License-Identifier: GPL-2.0-only
/*
 * Lab helper: enable VTOF_LDO_2P8 so userspace can talk to VL53L3 @ 0x29.
 * Not for upstream. Do not mail.
 */
#include <linux/module.h>
#include <linux/regulator/consumer.h>

static struct regulator *vtof;

static int __init tof_rail_init(void)
{
	int ret;

	vtof = regulator_get(NULL, "VTOF_LDO_2P8");
	if (IS_ERR(vtof)) {
		ret = PTR_ERR(vtof);
		vtof = NULL;
		pr_err("tof-rail: get VTOF_LDO_2P8 failed: %d\n", ret);
		return ret;
	}

	ret = regulator_enable(vtof);
	if (ret) {
		pr_err("tof-rail: enable failed: %d\n", ret);
		regulator_put(vtof);
		vtof = NULL;
		return ret;
	}

	pr_info("tof-rail: VTOF_LDO_2P8 enabled\n");
	return 0;
}

static void __exit tof_rail_exit(void)
{
	if (vtof) {
		regulator_disable(vtof);
		regulator_put(vtof);
		vtof = NULL;
		pr_info("tof-rail: VTOF_LDO_2P8 disabled\n");
	}
}

module_init(tof_rail_init);
module_exit(tof_rail_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Lab: enable Fairphone 5 VTOF_LDO_2P8");
