import easyconf

conf = easyconf.Config("settings.yaml")

PAT = conf.PAT(initial="")
EXPIRE_CACHE = conf.EXPIRE_CACHE(initial=60*10)
USER = conf.USER(initial="zodman")
