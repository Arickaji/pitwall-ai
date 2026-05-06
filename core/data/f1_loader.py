import fastf1

def load_race(year: int, gp: str, session_type: str):
    fastf1.Cache.enable_cache('data/cache')
    
    session = fastf1.get_session(year, gp, session_type)
    session.load()

    return session.laps