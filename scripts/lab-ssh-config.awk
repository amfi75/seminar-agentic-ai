# Preserve unrelated entries; add/adopt exactly one simple lab Host section.
function emit( i,k) {
 print "# BEGIN managed " alias
 print "Host " alias
 print "  HostName " address
 print "  User student"
 print "  IdentityFile \"" identity "\""
 print "  IdentitiesOnly yes"
 print "  HostKeyAlias " alias
 print "  UserKnownHostsFile \"" trust "\""
 print "  StrictHostKeyChecking yes"
 for(i=1;i<=extras;i++)print extra[i]
 print "# END managed " alias
 emitted=1
}
{
 if(NR==1 && /\r$/)ORS="\r\n"
 sub(/\r$/, "")
 line=$0
 if(operation=="open") {
  if(line=="# BEGIN managed " alias)managed=1
  if(managed && tolower($1)=="hostname")print "  HostName " address
  else print line
  if(line=="# END managed " alias)managed=0
  next
 }
 if(line=="# BEGIN managed " alias || line=="# END managed " alias)next
 if(tolower($1)=="match") {
  if(inside){emit();inside=0}
  # Match rules can override the alias; ssh -G must validate the final result.
 }
 if(tolower($1)=="host") {
  if(inside){emit();inside=0}
  matched=0
  for(i=2;i<=NF;i++)if(tolower($i)==tolower(alias))matched=1
  if(matched) {
   count++
   if(NF!=2 || count>1){print "Ambiguous/duplicate lab Host entry; preserve and resolve it." > "/dev/stderr";exit 2}
   inside=1;next
  }
 }
 if(inside) {
  k=tolower($1)
  if(k!="hostname" && k!="user" && k!="identityfile" && k!="identitiesonly" && k!="hostkeyalias" && k!="userknownhostsfile" && k!="stricthostkeychecking")extra[++extras]=line
 }else print line
}
END {if(operation!="open" && count<=1 && !emitted)emit()}
