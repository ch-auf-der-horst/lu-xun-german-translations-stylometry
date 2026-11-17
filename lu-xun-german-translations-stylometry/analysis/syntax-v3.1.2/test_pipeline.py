import unittest
import spacy
from pipeline import normalize,boundaries,detect_clauses,depths

class SyntaxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp=spacy.load('de_core_news_lg');cls.nlp.add_pipe('lu_xun_boundaries',before='parser')
    def test_preprocessing_and_provenance(self):
        raw='Das Tagebuch eines Verrückten. Ich weiß, dass {*chin*} kommt. 2. April 1918.'
        text,mapping,log=normalize(raw,'pref')
        self.assertEqual(text,'Ich weiß, dass Chin kommt.')
        i=text.index('kommt');self.assertEqual(raw[mapping[i]:mapping[i]+5],'kommt')
        self.assertEqual([x['rule'] for x in log].count('remove_pref_date'),1)
    def test_semicolon_parentheses_and_exclamation(self):
        doc=self.nlp('Er kam; sie blieb. Ich hörte (Rette dich!), dass er ging. Wirklich?! Ja.')
        self.assertEqual(len(list(doc.sents)),4)
        for s in doc.sents:depths(s,{t.i:t.head.i for t in s})
    def test_positive_and_negative_pairs(self):
        pairs=[('Was hat er getan?',0),('Ich weiß, was er getan hat.',1),('Wer kommt?',0),
          ('Wer kommt, wird begrüßt.',1),('Sie lacht und singt.',0),('Er sagt, er komme.',0),
          ('Er hofft, bald zu kommen.',0),('Er fragt, ob sie gehen will.',1),
          ('Wenn sie mich fressen können, fliehe ich.',1),('Er geht schnell, wie der Wind.',0),
          ('Ich sehe, wie schön sie ist mit ihrem Hut.',1),('Der Mann, der gestern gekommen ist, geht.',1),
          ('Ich kenne den Mann, der die Frau kennt, die hier wohnt.',2),
          ('Er fragte: Was für ein Glück du hast!',0),('Was du hast, ist mir egal.',1),
          ('Ich frage, was er macht und wohin er geht.',2),
          ('Die Worte, die er geschrieben, sind unklar.',0),
          ('Der Mann, den er erwartet, ist da.',1),('Er hat erwartet, dass sie kommt.',1),
          ('Nicht nur, dass sie kommen werden, sie bleiben auch.',1),
          ('Je älter er wird, desto ruhiger bleibt er.',1),('Er ist größer als ich.',0),
          ('Er lacht, als hätte er gewonnen.',1)]
        for text,n in pairs:
            with self.subTest(text=text):self.assertEqual(len(detect_clauses(self.nlp(text))[0]),n)
    def test_editorial_repairs_and_offsets(self):
        raw="V erfasset und V ersuch auf' geschlossen einlegte, Wie soll ich nun handeln?"
        text,mapping,log=normalize(raw,'diary')
        self.assertEqual(text,'Verfasser und Versuch aufgeschlossen einlegte. Wie soll ich nun handeln?')
        self.assertEqual(len(list(self.nlp(text).sents)),2)
        self.assertEqual(len(mapping),len(text))
        self.assertEqual(mapping,sorted(mapping))
        self.assertEqual(normalize(text,'diary')[0],text)
    def test_cycles_are_errors(self):
        doc=self.nlp('Er kommt.');s=list(doc.sents)[0]
        with self.assertRaises(ValueError):depths(s,{0:1,1:0,2:1})

    def test_pengkun_source_repair_offsets(self):
        raw='Der Brief wurde von Gläubigem an den Verlag geschickt.'
        text,mapping,log=normalize(raw,'diary','2019_Pengkun_cleaned')
        self.assertEqual(text,raw.replace('Gläubigem','Gläubigern'))
        self.assertEqual(len(text),len(mapping))
        self.assertEqual(mapping,sorted(mapping))
        i=text.index('Gläubigern');span=mapping[i:i+len('Gläubigern')]
        self.assertEqual(raw[min(span):max(span)+1],'Gläubigem')
        i=text.index('geschickt');self.assertEqual(raw[mapping[i]:mapping[i]+9],'geschickt')
        self.assertEqual(normalize(text,'diary','2019_Pengkun_cleaned')[0],text)
        self.assertEqual(normalize(raw,'diary','1994_Kubin_cleaned')[0],raw)
        self.assertEqual(sum(e['rule']=='restore_glaeubigern_pengkun_2019' for e in log),1)

if __name__=='__main__':unittest.main()
