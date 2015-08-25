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

# 1. �S���n�������c�̃R�[�h(JIS X0401�AX0402)�c�c�c�@���p����
# 2. (��) �X�֔ԍ�(5 ��)�c�c�c�c�c�c�c�c�c�c�c�c�c�c�c �@���p����
# 3. �X�֔ԍ�(7 ��)�c�c�c�c�c�c�c�c�c�c�c�c�c�c�c �@���p����
# 4. �s���{�����@�c�c�c�c�@���p�J�^�J�i(�R�[�h���Ɍf��)�@(��1)
# 5. �s�撬�����@�c�c�c�c�@���p�J�^�J�i(�R�[�h���Ɍf��)�@(��1)
# 6. ���於�@�c�c�c�c�c�c�@���p�J�^�J�i(�܏\�����Ɍf��)�@(��1)
# 7. �s���{�����@�c�c�c�c�@����(�R�[�h���Ɍf��)�@(��1,2)
# 8. �s�撬�����@�c�c�c�c�@����(�R�[�h���Ɍf��)�@(��1,2)
# 9. ���於�@�c�c�c�c�c�c�@����(�܏\�����Ɍf��)�@(��1,2)
# 10. �꒬�悪��ȏ�̗X�֔ԍ��ŕ\�����ꍇ�̕\���@(��3)
#    �@(�u1�v�͊Y���A�u0�v�͊Y������)
# 11. �������ɔԒn���N�Ԃ���Ă��钬��̕\���@(��4)
#    �@(�u1�v�͊Y���A�u0�v�͊Y������)
# 12. ���ڂ�L���钬��̏ꍇ�̕\���@(�u1�v�͊Y���A�u0�v�͊Y������)
# 13. ��̗X�֔ԍ��œ�ȏ�̒����\���ꍇ�̕\���@(��5)
#    �@(�u1�v�͊Y���A�u0�v�͊Y������)
# 14. �X�V�̕\���i��6�j
#     �i�u0�v�͕ύX�Ȃ��A�u1�v�͕ύX����A�u2�v�p�~�i�p�~�f�[�^�̂ݎg�p�j�j
# 15. �ύX���R
#    �@(�u0�v�͕ύX�Ȃ��A�u1�v�s���E�搭�E�����E����E���ߎw��s�s�{�s�A
#       �u2�v�Z���\���̎��{�A�u3�v��搮���A�u4�v�X�֋撲�����A�u5�v�����A
#       �u6�v�p�~(�p�~�f�[�^�̂ݎg�p))
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

