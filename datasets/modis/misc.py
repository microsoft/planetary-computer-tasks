# Add back in the platform property which NASA removed from their XML on March 13 2024
# On the MODIS side terra is distributed as MOD and aqua as MYD,
# but Within MPC both are distributed as MODxxx
def add_platform_field(item, href, logger):
    if ("platform" not in item.properties) or (item.properties["platform"] == ""):
        logger.debug("platform field missing, filling it in based on original xml href")
        try:
            if href.split('/')[4][0:3] == "MOD":
                item.properties["platform"] = "terra"
            elif href.split('/')[4][0:3] == "MYD":
                item.properties["platform"] = "aqua"
            elif href.split('/')[4][0:3] == "MCD":
                item.properties["platform"] = "terra,aqua"
            else:
                logger.warning("href did not contain MOD/MYD/MCD in the usual spot")
        except Exception as e:
            logger.warning(f"href did not contain MOD/MYD/MCD in the usual spot, got error: {e}")
    return item
