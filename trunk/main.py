#!/usr/bin/env python
# -*- coding: cp932 -*-
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import wsgiref.handlers
from zipfile import ZipFile
import csv, logging
from StringIO import StringIO
import os
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.api import users

# 1. 全国地方公共団体コード(JIS X0401、X0402)………　半角数字
# 2. (旧) 郵便番号(5 桁)……………………………………… 　半角数字
# 3. 郵便番号(7 桁)……………………………………… 　半角数字
# 4. 都道府県名　…………　半角カタカナ(コード順に掲載)　(注1)
# 5. 市区町村名　…………　半角カタカナ(コード順に掲載)　(注1)
# 6. 町域名　………………　半角カタカナ(五十音順に掲載)　(注1)
# 7. 都道府県名　…………　漢字(コード順に掲載)　(注1,2)
# 8. 市区町村名　…………　漢字(コード順に掲載)　(注1,2)
# 9. 町域名　………………　漢字(五十音順に掲載)　(注1,2)
# 10. 一町域が二以上の郵便番号で表される場合の表示　(注3)
#    　(「1」は該当、「0」は該当せず)
# 11. 小字毎に番地が起番されている町域の表示　(注4)
#    　(「1」は該当、「0」は該当せず)
# 12. 丁目を有する町域の場合の表示　(「1」は該当、「0」は該当せず)
# 13. 一つの郵便番号で二以上の町域を表す場合の表示　(注5)
#    　(「1」は該当、「0」は該当せず)
# 14. 更新の表示（注6）
#     （「0」は変更なし、「1」は変更あり、「2」廃止（廃止データのみ使用））
# 15. 変更理由
#    　(「0」は変更なし、「1」市政・区政・町政・分区・政令指定都市施行、
#       「2」住居表示の実施、「3」区画整理、「4」郵便区調整等、「5」訂正、
#       「6」廃止(廃止データのみ使用))
class Zipcode(db.Model):
  govcode = db.StringProperty()
  oldcode = db.StringProperty()
  code = db.StringProperty()
  kanapref = db.StringProperty()
  kanacity = db.StringProperty()
  kanastreet = db.StringProperty()
  pref = db.StringProperty()
  city = db.StringProperty()
  street = db.StringProperty()

  def __repr__(self):
    return u"%s,%s,%s,%s,%s,%s,%s,%s,%s" % (self.govcode,
                                            self.oldcode,
                                            self.code,
                                            self.kanapref,
                                            self.kanacity,
                                            self.kanastreet,
                                            self.pref,
                                            self.city,
                                            self.street)

  def from_file(fileobj):
    csvfile = csv.reader(fileobj)
    for row in csvfile:
      yield Zipcode(govcode=unicode(row[0], 'cp932'),
                    oldcode=unicode(row[1], 'cp932'),
                    code=unicode(row[2], 'cp932'),
                    kanapref=unicode(row[3], 'cp932'),
                    kanacity=unicode(row[4], 'cp932'),
                    kanastreet=unicode(row[5], 'cp932'),
                    pref=unicode(row[6], 'cp932'),
                    city=unicode(row[7], 'cp932'),
                    street=unicode(row[8], 'cp932'))
  from_file = staticmethod(from_file)
  def put(self):
    super(Zipcode, self).put()
    detail = []
    for n in [self.kanapref, self.kanacity, self.kanastreet, self.pref,
              self.city, self.street]:
      while len(n) > 1:
        detail.append(n)
        n = n[1:]
      detail.append(n)
    logging.info(detail)
    zipdetail = Zipdetail(code=self.key(), detail=detail)
    zipdetail.put()

class Zipdetail(db.Model):
  code = db.ReferenceProperty(Zipcode)
  detail = db.StringListProperty()

class MainHandler(webapp.RequestHandler):
  def get(self):
    template_values = {
      }
    path = os.path.join(os.path.dirname(__file__), "main.html")
    self.response.out.write(template.render(path, template_values))
  def post(self):
    query = self.request.get('query')
    logging.info(unicode(query))
    if not query:
      self.redirect(self.request.path)
    zipdetail = Zipdetail.all().filter('detail =',query).fetch(20)
    template_values = {
      'query':query,
      'zipdetail':zipdetail,
      }
    path = os.path.join(os.path.dirname(__file__), "main.html")
    self.response.out.write(template.render(path, template_values))

class SettingHandler(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.path))
    if not users.is_current_user_admin():
      self.redirect(users.create_login_url(self.request.path))
    template_values = {
      'zipcodes':Zipcode.all()
    }
    path = os.path.join(os.path.dirname(__file__), "setting.html")
    self.response.out.write(template.render(path, template_values))
  def post(self):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.path))
    if not users.is_current_user_admin():
      self.redirect(users.create_login_url(self.request.path))
    archivefile = self.request.get('FiletoUpload')
    logging.error(dir(archivefile))
    file = ZipFile(StringIO(archivefile))
    self.response.headers['Content-Type'] = 'text'
    for fname in file.namelist():
      f = StringIO(file.read(fname))
      for z in Zipcode.from_file(f):
        z.put()
    self.redirect(self.request.path)

def main():
  application = webapp.WSGIApplication([
          ('/', MainHandler),
          ('/setting', SettingHandler)
          ],
          debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()

