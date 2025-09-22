async def process_elite_upcoming_match(match):
    """Processa jogos futuros quando pelo menos uma equipe é de elite"""
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_team_id = match['teams']['home']['id']
    away_team_id = match['teams']['away']['id']
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    # Verificar se é um dos top 10 campeonatos
    if league_id not in TOP_LEAGUES:
        return
    
    # **CORREÇÃO: Verificar se pelo menos uma equipe é de elite**
    home_is_elite = home_team in EQUIPAS_DE_TITULO
    away_is_elite = away_team in EQUIPAS_DE_TITULO
    
    # Só prosseguir se pelo menos uma for de elite
    if not (home_is_elite or away_is_elite):
        return
    
    notification_key = f"elite_game_{fixture_id}"
    if notification_key not in notified_matches['elite_games']:
        
        match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
        match_time_local = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
        
        # Determinar qual(is) equipe(s) é(são) de elite
        if home_is_elite and away_is_elite:
            elite_status = "Ambas as equipes são de elite!"
            # Buscar stats de ambas
            try:
                home_elite_stats = analyze_elite_team_stats(home_team_id, league_id)
                away_elite_stats = analyze_elite_team_stats(away_team_id, league_id)
                
                stats_section = f"""
📊 <b>Estatísticas (últimas 3 temporadas):</b>

🏠 <b>{home_team}:</b>
• Vitórias: {home_elite_stats['win_percentage']}%
• Over 1.5 gols: {home_elite_stats['over_15_percentage']}%

✈️ <b>{away_team}:</b>
• Vitórias: {away_elite_stats['win_percentage']}%
• Over 1.5 gols: {away_elite_stats['over_15_percentage']}%
                """
            except:
                stats_section = "📊 <i>Carregando estatísticas...</i>"
                
        elif home_is_elite:
            elite_status = f"{home_team} é uma equipe de elite!"
            # Buscar stats só da equipe de elite
            try:
                home_elite_stats = analyze_elite_team_stats(home_team_id, league_id)
                stats_section = f"""
📊 <b>Estatísticas de {home_team} (últimas 3 temporadas):</b>
• Vitórias: {home_elite_stats['win_percentage']}%
• Over 1.5 gols: {home_elite_stats['over_15_percentage']}%
                """
            except:
                stats_section = f"📊 <i>Carregando estatísticas de {home_team}...</i>"
                
        else:  # away_is_elite
            elite_status = f"{away_team} é uma equipe de elite!"
            # Buscar stats só da equipe de elite
            try:
                away_elite_stats = analyze_elite_team_stats(away_team_id, league_id)
                stats_section = f"""
📊 <b>Estatísticas de {away_team} (últimas 3 temporadas):</b>
• Vitórias: {away_elite_stats['win_percentage']}%
• Over 1.5 gols: {away_elite_stats['over_15_percentage']}%
                """
            except:
                stats_section = f"📊 <i>Carregando estatísticas de {away_team}...</i>"
        
        message = f"""
⭐ <b>JOGO DO DIA - EQUIPE DE ELITE</b> ⭐

🏆 <b>{TOP_LEAGUES[league_id]}</b>
⚽ <b>{home_team} vs {away_team}</b>

👑 {elite_status}

🕐 <b>{match_time_local.strftime('%H:%M')} (Lisboa)</b>
📅 {match_time_local.strftime('%d/%m/%Y')}

{stats_section}

🔥 Jogo de alto nível!
        """
        
        await send_telegram_message(message)
        notified_matches['elite_games'].add(notification_key)
        logger.info(f"✅ Jogo do dia notificado: {home_team} vs {away_team}")

async def process_elite_finished_match(match):
    """Processa jogos finalizados quando pelo menos uma equipe é de elite para Under 1.5"""
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_team_id = match['teams']['home']['id']
    away_team_id = match['teams']['away']['id']
    home_goals = match['goals']['home'] or 0
    away_goals = match['goals']['away'] or 0
    total_goals = home_goals + away_goals
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    # Verificar se é um dos top 10 campeonatos
    if league_id not in TOP_LEAGUES:
        return
    
    # **CORREÇÃO: Verificar se pelo menos uma equipe é de elite**
    home_is_elite = home_team in EQUIPAS_DE_TITULO
    away_is_elite = away_team in EQUIPAS_DE_TITULO
    
    # Verificar Under 1.5 gols E pelo menos uma equipe de elite
    if (home_is_elite or away_is_elite) and total_goals < 2:
        notification_key = f"under15_{fixture_id}"
        if notification_key not in notified_matches['under_15']:
            
            # Determinar qual(is) equipe(s) é(são) de elite e buscar stats
            if home_is_elite and away_is_elite:
                elite_status = "Ambas as equipes são de elite!"
                try:
                    home_elite_stats = analyze_elite_team_stats(home_team_id, league_id)
                    away_elite_stats = analyze_elite_team_stats(away_team_id, league_id)
                    
                    stats_section = f"""
📈 <b>Estatísticas das equipes (últimas 3 temporadas):</b>

🏠 <b>{home_team}:</b>
• Vitórias: {home_elite_stats['win_percentage']}%
• Over 1.5 gols: {home_elite_stats['over_15_percentage']}%

✈️ <b>{away_team}:</b>
• Vitórias: {away_elite_stats['win_percentage']}%
• Over 1.5 gols: {away_elite_stats['over_15_percentage']}%
                    """
                except:
                    stats_section = "📈 <i>Erro ao carregar estatísticas</i>"
                    
            elif home_is_elite:
                elite_status = f"{home_team} é uma equipe de elite!"
                try:
                    home_elite_stats = analyze_elite_team_stats(home_team_id, league_id)
                    stats_section = f"""
📈 <b>Estatísticas de {home_team} (últimas 3 temporadas):</b>
• Vitórias: {home_elite_stats['win_percentage']}%
• Over 1.5 gols: {home_elite_stats['over_15_percentage']}%
                    """
                except:
                    stats_section = f"📈 <i>Erro ao carregar estatísticas de {home_team}</i>"
                    
            else:  # away_is_elite
                elite_status = f"{away_team} é uma equipe de elite!"
                try:
                    away_elite_stats = analyze_elite_team_stats(away_team_id, league_id)
                    stats_section = f"""
📈 <b>Estatísticas de {away_team} (últimas 3 temporadas):</b>
• Vitórias: {away_elite_stats['win_percentage']}%
• Over 1.5 gols: {away_elite_stats['over_15_percentage']}%
                    """
                except:
                    stats_section = f"📈 <i>Erro ao carregar estatísticas de {away_team}</i>"
            
            message = f"""
📉 <b>UNDER 1.5 GOLS - EQUIPE DE ELITE</b> 📉

🏆 <b>{TOP_LEAGUES[league_id]}</b>
⚽ <b>{home_team} {home_goals} x {away_goals} {away_team}</b>

👑 {elite_status}
📊 Total de gols: {total_goals} (Under 1.5 ✅)

{stats_section}

🎯 Oportunidade identificada com equipe de elite!

🕐 <i>{datetime.now(ZoneInfo("Europe/Lisbon")).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>
            """
            
            await send_telegram_message(message)
            notified_matches['under_15'].add(notification_key)
