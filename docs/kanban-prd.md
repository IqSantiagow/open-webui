# Kanban Board - PRD

Tablica kanban wbudowana w Open WebUI, sluzaca do organizacji pracy uzytkownika
oraz pracy agentow. Agenci maja pelny dostep r/w przez REST API i wbudowany tool.

## Cel

- Jedno miejsce do sledzenia zadan wlasnych i zadan delegowanych agentom.
- Agenci moga samodzielnie tworzyc, aktualizowac i przesuwac karty w trakcie pracy.
- Pelny audyt: kazda akcja (czlowieka i agenta) zapisuje wpis aktywnosci.

## Decyzje projektowe

| Obszar          | Decyzja                                                                             |
| --------------- | ----------------------------------------------------------------------------------- |
| Layout          | Kanban + staly panel szczegolow po prawej (wariant B)                               |
| Szczegoly karty | Klik = szybki podglad w panelu; "Rozwin" / dwuklik = modal `md` (dwie kolumny)      |
| Osadzenie       | Zakladka w Workspace: `Models / Knowledge / Prompts / Tools / Kanban`               |
| Dostep agentow  | REST API (`/api/v1/kanban/...`) + wbudowany tool wolany przez modele w czacie       |
| Kolumny         | W pelni customizowalne: nazwa, kolejnosc (drag&drop / reorder), dodawanie, usuwanie |
| Tablice         | Wiele tablic na uzytkownika, przelaczane selektorem; wybor pamietany w localStorage |
| Foldery         | Tablica moze byc podpieta do folderu (`folder_id`); selektor grupuje wg folderow |

## Mockup - widok glowny

```
Workspace > [ Models | Knowledge | Prompts | Tools | Kanban ]
+---------------------------------------------+---------------------------+
| [Szukaj...]  [Filtr: wszyscy v] [+ Kolumna] |  Fix auth flow   [::] [x] |
+---------------------------------------------+---------------------------+
|  Backlog (3)    In Progress (2)  Review (1) |  Status  [In Progress v]  |
|  +----------+   +----------+   +---------+  |  Owner   [@agent-1    v]  |
|  | Karta 1  |   |*Karta 5 *|   | Karta 7 |  |  Prio    [Wysoki      v]  |
|  | @agent-1 |   | @ja  !hi |   | @agent-2|  |  Tagi    [bug] [auth]     |
|  +----------+   +----------+   +---------+  |  -----------------------  |
|  | Karta 2  |   | Karta 6  |                |  Opis                     |
|  +----------+   +----------+                |  Naprawic OAuth redirect  |
|  | Karta 3  |                               |  gubi state param...      |
|  +----------+   [+ Karta]      [+ Karta]    |  -----------------------  |
|  [+ Karta]                                  |  Aktywnosc                |
|                                             |  - agent-1: moved -> IP   |
|   <-- drag&drop kart i kolumn, poziomy      |  - ja: created            |
|       scroll -->                            |  [Rozwin do pelnej karty] |
+---------------------------------------------+---------------------------+
[::] = rozwin modal md (pelna edycja markdown + komentarze)
```

## Mockup - modal szczegolow karty (size="md", 42rem)

```
+------------------------------------------------------+
|  Fix auth flow                                  [x]  |
+------------------------------------------------------+
|                                    |  Status         |
|  Opis                              |  [In Progress v]|
|  +------------------------------+  |                 |
|  | Naprawic logowanie OAuth,    |  |  Przypisany     |
|  | redirect gubi state param.   |  |  [@agent-1   v] |
|  | (markdown)                   |  |                 |
|  +------------------------------+  |  Priorytet      |
|                                    |  [Wysoki     v] |
|  Aktywnosc                         |                 |
|  - agent-1: rozpoczal prace  2h    |  Tagi           |
|  - ja: utworzyl karte        5h    |  [bug] [auth]   |
|                                    |                 |
|  [Komentarz...            ] [>]    |  Utw. 2026-08-22|
+------------------------------------+-----------------+
```

## Mockup - selektor tablic

```
[Tablica: Praca v] [*]
+-------------------------------+
| [Szukaj tablicy...]           |
| -- Projekt A (folder) ------- |
|   Praca              [check]  |
|   Backend                 3   |
| -- Bez folderu -------------- |
|   Szkice                  7   |
| ----------------------------- |
| + Nowa tablica                |
+-------------------------------+
Liczba po prawej = liczba kart. [*] = ustawienia tablicy (nazwa, folder, usuniecie).
```

## Zachowanie UI

- Klik na karte: zaznaczenie + podglad w prawym panelu (bez przeladowania widoku).
- Dwuklik albo przycisk `[::]` w panelu: modal `md` z pelna edycja opisu (markdown)
  i komentarzami.
- Drag&drop: karty miedzy kolumnami i w obrebie kolumny; kolumny przestawialne
  w poziomie. Biblioteka: `svelte-dnd-action` (nowa zaleznosc) albo natywny
  HTML5 drag - decyzja przy implementacji.
- Karta na tablicy pokazuje: tytul, badge ownera (@ja / @agent-x), kropke
  priorytetu (jedyny akcent kolorystyczny, styl jak `Badge.svelte`), liczbe
  komentarzy.
- Toolbar: selektor tablic, ustawienia tablicy, wyszukiwarka, filtr po ownerze.
- Przelaczenie tablicy zamyka panel szczegolow i przeladowuje kolumny.
- Usuniecie folderu tylko odpina tablice (`folder_id` -> `NULL`), nie kasuje ich.
- Kazda kolumna ma licznik kart i przycisk `+ Karta` na dole.
- Odswiezanie live: socket.io (OWU ma juz infrastrukture socketow) - zmiany
  wykonane przez agentow pojawiaja sie na tablicy bez odswiezania. Fallback:
  polling co ~10 s.

## Model danych (`backend/open_webui/models/kanban.py`)

- `kanban_board`: `id`, `user_id`, `folder_id`, `name`, `meta`, `created_at`, `updated_at`
- `kanban_column`: `id`, `board_id`, `name`, `order`, `created_at`
- `kanban_card`: `id`, `column_id`, `title`, `description` (markdown),
  `order`, `owner`, `assigned_agent`, `priority` (`low|medium|high`),
  `tags` (json), `meta` (json), `created_at`, `updated_at`
- `kanban_activity`: `id`, `card_id`, `actor` (user id albo nazwa agenta),
  `action` (`created|updated|moved|commented|deleted`), `payload` (json),
  `timestamp`

## REST API (`backend/open_webui/routers/kanban.py`)

Prefiks: `/api/v1/kanban`. Autoryzacja: istniejacy mechanizm OWU
(sesja lub API key) - agenci uzywaja API key.

| Metoda | Endpoint               | Opis                                                    |
| ------ | ---------------------- | ------------------------------------------------------- |
| GET    | `/boards`              | Lista tablic z `folder_id` i liczba kart                |
| POST   | `/boards`              | Nowa tablica (z domyslnym zestawem kolumn)              |
| POST   | `/boards/{id}/update`  | Zmiana nazwy i/lub folderu                              |
| DELETE | `/boards/{id}`         | Usuniecie tablicy z kolumnami, kartami i aktywnoscia    |
| GET    | `/board?board_id=`     | Cala tablica: kolumny + karty (posortowane po `order`)  |
| POST   | `/columns?board_id=`   | Nowa kolumna                                            |
| PATCH  | `/columns/{id}`        | Zmiana nazwy                                            |
| DELETE | `/columns/{id}`        | Usuniecie (karty przenoszone albo blokada gdy niepusta) |
| POST   | `/columns/reorder?board_id=` | Nowa kolejnosc kolumn (lista id)                  |
| POST   | `/cards`               | Nowa karta                                              |
| PATCH  | `/cards/{id}`          | Aktualizacja pol karty                                  |
| DELETE | `/cards/{id}`          | Usuniecie karty                                         |
| POST   | `/cards/{id}/move`     | Przeniesienie: `column_id` + `position`                 |
| GET    | `/cards/{id}/activity` | Historia aktywnosci karty                               |
| POST   | `/cards/{id}/comment`  | Komentarz (wpis aktywnosci typu `commented`)            |

Kazdy zapis tworzy wpis w `kanban_activity` z aktorem wyciagnietym z autoryzacji.

## Tool wbudowany (dostep agentow z czatu)

Natywny tool OWU, funkcje dostepne dla modeli:

- `kanban_list_boards()` - lista tablic (id, nazwa, folder, liczba kart)
- `kanban_list_cards(board, column, owner, tag, query, count)`
- `kanban_create_card(title, column, board, description, priority, tags)`
- `kanban_update_card(card_id, ...pola)`
- `kanban_move_card(card_id, column, position)`
- `kanban_comment(card_id, text)`
- `kanban_card_activity(card_id, count)`

Tablice i kolumny mozna wskazywac po nazwie albo po ID. Bez podanej tablicy agent
pracuje na pierwszej tablicy uzytkownika. Operacje na istniejacej karcie (`update`,
`move`, `comment`, `activity`) same rozpoznaja tablice, do ktorej karta nalezy.

Akcje toola loguja aktora jako nazwe agenta/modelu - pelny audyt w aktywnosci.

## Frontend (`src/lib/components/workspace/Kanban/`)

- `Kanban.svelte` - strona zakladki: toolbar + layout tablica/panel
- `BoardSelector.svelte` - selektor tablic z grupowaniem po folderach + "Nowa tablica"
- `BoardModal.svelte` - tworzenie/edycja tablicy (nazwa, folder, usuniecie)
- `Board.svelte` - kontener kolumn, poziomy scroll, dnd kolumn
- `Column.svelte` - naglowek (nazwa, licznik, menu), lista kart, `+ Karta`
- `Card.svelte` - karta na tablicy
- `CardPanel.svelte` - prawy panel podgladu (szkielet klas jak Controls w czacie)
- `CardModal.svelte` - `Modal size="md"`, dwie kolumny
- API client: `src/lib/apis/kanban/index.ts`
- Routing: nowa zakladka w istniejacym layoucie Workspace

Styl zgodny ze skillem `openwebui-design`: pary `light dark:`, tokeny `gray`,
`rounded-xl`, plaski UI, teksty przez `$i18n.t()`, prymitywy z
`src/lib/components/common/`.

## Poza zakresem

- Uprawnienia per-tablica / wspoldzielenie miedzy uzytkownikami
- Tablice widoczne w drzewie folderow w lewym sidebarze
- Zaleznosci miedzy kartami, terminy, powiadomienia
- Widok listy/tabeli (wariant D - mozliwe rozszerzenie)

## Kryteria akceptacji

1. CRUD kolumn i kart z UI oraz przez REST API dziala identycznie.
2. Drag&drop kart i kolumn zapisuje kolejnosc trwale.
3. Agent w czacie potrafi przez tool utworzyc, zaktualizowac i przesunac karte.
4. Kazda akcja agenta jest widoczna w aktywnosci karty z nazwa aktora.
5. Zmiany od agentow pojawiaja sie na otwartej tablicy bez odswiezania strony.
6. UI poprawny w motywach light / dark / oled-dark, `npm run format` i
   `npm run check` przechodza.
7. Uzytkownik moze tworzyc, przelaczac, edytowac i usuwac tablice; wybor tablicy
   przezywa przeladowanie strony.
8. Tablice mozna podpiac do folderu, a usuniecie folderu tylko je odpina.
