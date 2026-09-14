"""Recovering an artist and a track from a YouTube title.

These are real title shapes. The failure they guard against is quiet: a lookup
for a track called "Rap God (Explicit) [Official Video] (4K)" matches nothing,
so the song looks absent from every lyrics database when the query was simply
malformed.
"""

from __future__ import annotations

import unittest

from rhymemap.sources.titles import (
    clean_channel,
    from_metadata,
    is_noise_group,
    parse_title,
    split_featured,
    strip_noise,
)


class TestNoiseGroups(unittest.TestCase):
    def test_packaging_is_noise(self):
        for inner in ("Official Video", "OFFICIAL MUSIC VIDEO", "Lyrics", "Official Audio",
                      "Explicit", "HD", "4K", "Remastered", "2019", "Visualizer",
                      "with lyrics", "Closed Captions", "official video hd"):
            with self.subTest(inner=inner):
                self.assertTrue(is_noise_group(inner))

    def test_parts_of_the_name_are_not_noise(self):
        for inner in ("Remix", "Interlude", "Album Version", "feat. Drake", "Skit",
                      "Live at Wembley", "Deluxe", "with Rihanna", "Part 2"):
            with self.subTest(inner=inner):
                self.assertFalse(is_noise_group(inner))


class TestStripNoise(unittest.TestCase):
    def test_removes_bracketed_packaging(self):
        self.assertEqual(
            strip_noise("Eminem - Rap God (Explicit) [Official Video] (4K)"),
            "Eminem - Rap God")

    def test_removes_unbracketed_trailing_packaging(self):
        self.assertEqual(strip_noise("Eminem - Lose Yourself - Official Video"),
                         "Eminem - Lose Yourself")

    def test_keeps_meaningful_brackets(self):
        self.assertEqual(strip_noise("Kanye West - Stronger (Remix) [Official Audio]"),
                         "Kanye West - Stronger (Remix)")

    def test_trims_a_trailing_upload_year(self):
        self.assertEqual(strip_noise("J. Cole - MIDDLE CHILD (Official Music Video) [HD] 2019"),
                         "J. Cole - MIDDLE CHILD")

    def test_a_song_named_after_a_year_survives(self):
        """The year rule must not eat a track called 1999."""
        self.assertEqual(strip_noise("Joey Bada$$ - 1999"), "Joey Bada$$ - 1999")

    def test_adjacent_groups_are_all_removed(self):
        self.assertEqual(strip_noise("Artist - Song (Official)(Video)[HD]"), "Artist - Song")


class TestFeatured(unittest.TestCase):
    def test_splits_ft(self):
        self.assertEqual(split_featured("SICKO MODE ft. Drake"), ("SICKO MODE", "Drake"))

    def test_splits_feat_in_brackets(self):
        track, who = split_featured("a lot (feat. J. Cole)")
        self.assertEqual(track, "a lot")
        self.assertEqual(who, "J. Cole")

    def test_leaves_a_plain_title_alone(self):
        self.assertEqual(split_featured("Rap God"), ("Rap God", ""))

    def test_does_not_fire_on_a_word_merely_starting_with_ft(self):
        self.assertEqual(split_featured("Often")[0], "Often")


class TestCleanChannel(unittest.TestCase):
    def test_strips_topic(self):
        self.assertEqual(clean_channel("Kendrick Lamar - Topic"), "Kendrick Lamar")

    def test_strips_vevo(self):
        self.assertEqual(clean_channel("EminemVEVO"), "Eminem")

    def test_leaves_a_plain_name(self):
        self.assertEqual(clean_channel("NFrealmusic"), "NFrealmusic")


class TestParseTitle(unittest.TestCase):
    CASES = [
        ("Eminem - Rap God (Explicit) [Official Video] (4K)", "EminemMusic", "Eminem", "Rap God"),
        ("Travis Scott - SICKO MODE ft. Drake", "TravisScottVEVO", "Travis Scott", "SICKO MODE"),
        ("NF - The Search (Official Video)", "NFrealmusic", "NF", "The Search"),
        ("Kendrick Lamar - HUMBLE.", "KendrickLamarVEVO", "Kendrick Lamar", "HUMBLE."),
        ("Eminem - Lose Yourself - Official Video", "Eminem", "Eminem", "Lose Yourself"),
        ("Tyler, The Creator - EARFQUAKE (Official Video)", "Tyler", "Tyler, The Creator", "EARFQUAKE"),
        ("J. Cole - MIDDLE CHILD (Official Music Video) [HD] 2019", "JColeVEVO", "J. Cole", "MIDDLE CHILD"),
        ("Doja Cat - Paint The Town Red (Official Video)", "DojaCatVEVO", "Doja Cat", "Paint The Town Red"),
    ]

    def test_real_titles(self):
        for title, channel, artist, track in self.CASES:
            with self.subTest(title=title):
                name = parse_title(title, channel)
                self.assertEqual(name.artist, artist)
                self.assertEqual(name.track, track)

    def test_no_dash_falls_back_to_the_channel(self):
        """A song uploaded bare is usually on the artist's own channel."""
        name = parse_title("HUMBLE.", "Kendrick Lamar - Topic")
        self.assertEqual(name.artist, "Kendrick Lamar")
        self.assertEqual(name.track, "HUMBLE.")

    def test_typographic_dashes_split_too(self):
        self.assertEqual(parse_title("Eminem – Stan", "x").track, "Stan")

    def test_quoted_track_names_are_unquoted(self):
        self.assertEqual(parse_title('Nas - "The Message"', "x").track, "The Message")

    def test_featured_artist_is_separated(self):
        name = parse_title("21 Savage - a lot (Official Video) ft. J. Cole", "21SavageVEVO")
        self.assertEqual(name.track, "a lot")
        self.assertEqual(name.featured, "J. Cole")

    def test_empty_title_is_falsy(self):
        self.assertFalse(parse_title("", ""))

    def test_query_joins_artist_and_track(self):
        self.assertEqual(parse_title("Eminem - Stan", "x").query, "Eminem Stan")


class TestFromMetadata(unittest.TestCase):
    def test_music_metadata_wins_over_the_title(self):
        """Videos matched to a release carry authoritative fields."""
        name = from_metadata({
            "track": "Rap God", "artist": "Eminem",
            "title": "Eminem - Rap God (Explicit) [Official Video]",
            "uploader": "EminemMusic",
        })
        self.assertEqual(name.artist, "Eminem")
        self.assertEqual(name.track, "Rap God")

    def test_multi_artist_metadata_keeps_the_primary(self):
        name = from_metadata({"track": "SICKO MODE", "artist": "Travis Scott, Drake"})
        self.assertEqual(name.artist, "Travis Scott")
        self.assertIn("Drake", name.featured)

    def test_falls_back_to_parsing_the_title(self):
        name = from_metadata({"title": "Eminem - Stan (Official Video)", "uploader": "EminemVEVO"})
        self.assertEqual(name.artist, "Eminem")
        self.assertEqual(name.track, "Stan")

    def test_empty_metadata_is_survivable(self):
        self.assertFalse(from_metadata({}))


if __name__ == "__main__":
    unittest.main()
