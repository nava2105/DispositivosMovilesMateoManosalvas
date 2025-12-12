import requests
import json
import time
import pandas as pd
from datetime import datetime


class InstagramProfileScraper:
    def __init__(self, session_id, csrf_token, user_agent=None):
        self.session = requests.Session()
        self.base_url = "https://i.instagram.com/api/v1"

        self.headers = {
            'user-agent': user_agent or 'Instagram 269.0.0.18.75 Android (30/11; 420dpi; 1080x1920; OnePlus; HD1913; OnePlus 7T; qcom; es_ES; 382214478)',
            'x-ig-app-id': '936619743392459',
            'x-asbd-id': '359341',
            'x-csrftoken': csrf_token,
            'x-requested-with': 'XMLHttpRequest',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'accept': '*/*',
            'accept-language': 'es,es-ES;q=0.9',
            'origin': 'https://www.instagram.com',
            'referer': 'https://www.instagram.com',
        }

        self.session.cookies.set('sessionid', session_id)
        self.session.cookies.set('csrftoken', csrf_token)

    def get_user_info(self, user_id):
        """Obtiene información detallada de un usuario"""
        url = f"{self.base_url}/users/{user_id}/info/"

        try:
            response = self.session.get(url, headers=self.headers)

            if response.status_code == 429:
                print(f"⚠️  Rate limit. Esperando 30s...")
                time.sleep(30)
                return self.get_user_info(user_id)

            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code} para user_id {user_id}")
                return None

            data = response.json().get('user', {})
            if not data:
                return None

            # Determinar tipo de cuenta
            account_type = "Personal"
            if data.get('is_business'):
                account_type = "Empresa"
            elif data.get('is_creator'):
                account_type = "Creador"

            # Extraer categoría si existe
            category = data.get('category', '')

            # Construir URL del perfil
            username = data.get('username', '')
            profile_url = f"https://www.instagram.com/{username}/" if username else ""

            return {
                'full_name': data.get('full_name', ''),
                'username': username,
                'biography': data.get('biography', '').replace('\n', ' '),
                'account_type': account_type,
                'category': category,
                'follower_count': data.get('follower_count', 0),
                'following_count': data.get('following_count', 0),
                'profile_url': profile_url,
                'is_verified': data.get('is_verified', False),
                'is_private': data.get('is_private', False),
            }

        except Exception as e:
            print(f"❌ Error obteniendo info de user_id {user_id}: {e}")
            return None

    def get_following(self, user_id, max_users=None, batch_delay=5, individual_delay=8):
        """Obtiene la lista de usuarios seguidos con información completa"""
        url = f"{self.base_url}/friendships/{user_id}/following/"

        all_profiles = []
        next_max_id = None
        has_more = True

        print(f"\n🔄 Iniciando extracción para user_id: {user_id}")
        print(f"⏳ Delay: {batch_delay}s entre lotes, {individual_delay}s por usuario\n")

        while has_more and (max_users is None or len(all_profiles) < max_users):
            params = {'count': 50}
            if next_max_id:
                params['max_id'] = next_max_id

            try:
                response = self.session.get(url, headers=self.headers, params=params)

                if response.status_code == 429:
                    print("⚠️  Rate limit alcanzado. Esperando 60s...")
                    time.sleep(60)
                    continue

                if response.status_code == 401:
                    print("❌ Error: Sesión no válida. Revisa las cookies.")
                    break

                if response.status_code != 200:
                    print(f"❌ HTTP {response.status_code}: {response.text}")
                    break

                data = response.json()
                users = data.get('users', [])

                if not users:
                    print("⚠️  No se encontraron más usuarios")
                    break

                print(f"✅ Lote de {len(users)} usuarios | Total acumulado: {len(all_profiles) + len(users)}")

                for user in users:
                    if max_users and len(all_profiles) >= max_users:
                        break

                    user_pk = user.get('pk')
                    username = user.get('username', 'N/A')

                    print(f"[{len(all_profiles) + 1}/{max_users or '?'}] Obteniendo @{username}...", end=" ",
                          flush=True)

                    profile_info = self.get_user_info(user_pk)

                    if profile_info:
                        all_profiles.append(profile_info)
                        print(f"✓ {profile_info['follower_count']:,} seguidores")
                    else:
                        # Si falla, guardar datos básicos
                        basic_info = {
                            'full_name': user.get('full_name', ''),
                            'username': username,
                            'biography': '',
                            'account_type': 'Personal',
                            'category': '',
                            'follower_count': 0,
                            'following_count': 0,
                            'profile_url': f"https://www.instagram.com/{username}/",
                            'is_verified': user.get('is_verified', False),
                            'is_private': user.get('is_private', False),
                        }
                        all_profiles.append(basic_info)
                        print(f"⚠️ Usando datos básicos")

                    time.sleep(individual_delay)

                next_max_id = data.get('next_max_id')
                has_more = data.get('has_more', False) and next_max_id

                if has_more and (max_users is None or len(all_profiles) < max_users):
                    time.sleep(batch_delay)

            except Exception as e:
                print(f"❌ Error inesperado: {e}")
                break

        return all_profiles


def main():
    print("=" * 60)
    print("INSTAGRAM FOLLOWING SCRAPER v2.0")
    print("=" * 60)
    print()

    print("⚠️  REQUISITOS:")
    print("   - Sesión válida en Instagram")
    print("   - User ID numérico del perfil objetivo")
    print()

    user_id = input("🔢 User ID: ").strip()
    session_id = input("🔑 SessionID: ").strip()
    csrf_token = input("🛡️  CSRF Token: ").strip()

    max_users = input("🎯 Máximo usuarios (Enter = sin límite): ").strip()
    max_users = int(max_users) if max_users else None

    batch_delay = input("⏱️  Delay entre lotes (seg, Enter=5): ").strip() or "5"
    individual_delay = input("⏱️  Delay por usuario (seg, Enter=8): ").strip() or "8"

    scraper = InstagramProfileScraper(session_id, csrf_token)

    profiles = scraper.get_following(
        user_id,
        max_users=max_users,
        batch_delay=float(batch_delay),
        individual_delay=float(individual_delay)
    )

    if profiles:
        print(f"\n✅ Extracción completada. {len(profiles)} perfiles obtenidos.")

        save = input("\n💾 Guardar en Excel? (s/n): ")
        if save.lower() == 's':
            try:
                df = pd.DataFrame(profiles)

                # Ordenar columnas
                column_order = [
                    'full_name',
                    'username',
                    'biography',
                    'account_type',
                    'category',
                    'follower_count',
                    'following_count',
                    'profile_url',
                    'is_verified',
                    'is_private'
                ]
                df = df[column_order]

                # Formato para números
                df['follower_count'] = df['follower_count'].astype(int)
                df['following_count'] = df['following_count'].astype(int)

                filename = f"following_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Seguidos', index=False)

                    # Ajustar ancho de columnas
                    worksheet = writer.sheets['Seguidos']
                    worksheet.column_dimensions['A'].width = 20  # full_name
                    worksheet.column_dimensions['B'].width = 15  # username
                    worksheet.column_dimensions['C'].width = 40  # biography
                    worksheet.column_dimensions['D'].width = 12  # account_type
                    worksheet.column_dimensions['E'].width = 20  # category
                    worksheet.column_dimensions['F'].width = 15  # follower_count
                    worksheet.column_dimensions['G'].width = 15  # following_count
                    worksheet.column_dimensions['H'].width = 30  # profile_url

                print(f"✅ Archivo Excel guardado: {filename}")

            except ImportError:
                print("❌ Error: Instala las dependencias:")
                print("   pip install pandas openpyxl")
            except Exception as e:
                print(f"❌ Error al guardar: {e}")
    else:
        print("\n❌ No se pudo obtener la lista de seguidos")


if __name__ == "__main__":
    main()